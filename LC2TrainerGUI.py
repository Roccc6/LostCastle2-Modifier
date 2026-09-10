import tkinter as tk
from tkinter import ttk, messagebox
import frida, queue, os, json

BASE = os.path.dirname(os.path.abspath(__file__))
AGENT_PATH = os.path.join(BASE, 'agent.js')
AFFIX_PATH = os.path.join(BASE, 'gem_affix.json')
ITEMS_PATH = os.path.join(BASE, 'items_give.json')
RES_TYPES = [('金币', 5), ('魂晶碎片', 4), ('魔铁锭', 7), ('黑铁原石', 60), ('魂花', 14)]
CATS = ['武器', '防具', '被动宝藏', '主动道具', '消耗品']

def load_json(path, default):
    try:
        return json.load(open(path, encoding='utf-8'))
    except Exception:
        return default

class App:
    def __init__(self, root):
        self.root = root
        root.title('Lost Castle 2 Trainer - 离线单机')
        root.geometry('780x700')
        self.session = None; self.script = None; self.api = None
        self.mq = queue.Queue()
        rows = load_json(AFFIX_PATH, [])
        self.affix_labels = [f"[{r['slot']}|{r['rare']}] {r['name']} ({r['id']})" for r in rows]
        self.affix_map = {f"[{r['slot']}|{r['rare']}] {r['name']} ({r['id']})": r['id'] for r in rows}
        self.sub_labels = ['【无】仅主词条（单词条石头）'] + self.affix_labels
        self.sub_map = {'【无】仅主词条（单词条石头）': ''}
        self.sub_map.update(self.affix_map)
        self.items = load_json(ITEMS_PATH, [])
        self.item_map = {}

        pad = {'padx': 8, 'pady': 4}
        top = ttk.Frame(root); top.pack(fill='x', **pad)
        ttk.Label(top, text='状态：').pack(side='left')
        self.status_var = tk.StringVar(value='未连接（请先在离线单机中启动游戏）')
        ttk.Label(top, textvariable=self.status_var).pack(side='left')
        ttk.Button(top, text='连接游戏', command=self.connect).pack(side='right')
        ttk.Button(top, text='刷新状态', command=lambda: self.send('status')).pack(side='right', padx=6)

        frm_res = ttk.LabelFrame(root, text='资源 / 货币（当前局）'); frm_res.pack(fill='x', **pad)
        ttk.Label(frm_res, text='类型：').grid(row=0, column=0, sticky='e', padx=4, pady=3)
        self.res_combo = ttk.Combobox(frm_res, state='readonly', width=14, values=[n for n, c in RES_TYPES])
        self.res_combo.current(0); self.res_combo.grid(row=0, column=1, sticky='w', pady=3)
        self.res_combo.bind('<<ComboboxSelected>>', self.on_res_change)
        ttk.Label(frm_res, text='数量：').grid(row=0, column=2, sticky='e', padx=4, pady=3)
        self.res_entry = ttk.Entry(frm_res, width=12); self.res_entry.grid(row=0, column=3, sticky='w'); self.res_entry.insert(0, '1000')
        ttk.Label(frm_res, text='等级：').grid(row=1, column=0, sticky='e', padx=4, pady=3)
        self.res_level = ttk.Spinbox(frm_res, from_=0, to=6, width=5); self.res_level.set('0'); self.res_level.grid(row=1, column=1, sticky='w', pady=3)
        ttk.Button(frm_res, text='增加', command=self.res_add).grid(row=0, column=4, padx=8)
        ttk.Button(frm_res, text='设为', command=self.res_set).grid(row=1, column=4, padx=8)
        self.on_res_change()

        frm_item = ttk.LabelFrame(root, text='获取装备 / 宝藏（直接进包）'); frm_item.pack(fill='x', **pad)
        ttk.Label(frm_item, text='分类：').grid(row=0, column=0, sticky='e', padx=4, pady=3)
        self.cat_combo = ttk.Combobox(frm_item, state='readonly', width=12, values=CATS)
        self.cat_combo.current(0); self.cat_combo.grid(row=0, column=1, sticky='w', pady=3)
        self.cat_combo.bind('<<ComboboxSelected>>', self.on_cat_change)
        ttk.Label(frm_item, text='物品：').grid(row=1, column=0, sticky='e', padx=4, pady=3)
        self.item_combo = ttk.Combobox(frm_item, state='readonly', width=60); self.item_combo.grid(row=1, column=1, columnspan=3, sticky='w', pady=3)
        self.drop_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frm_item, text='旧装备丢到地上', variable=self.drop_var).grid(row=2, column=1, sticky='w', pady=3)
        ttk.Button(frm_item, text='获取', command=self.give_item).grid(row=2, column=2, sticky='w', padx=6, pady=3)
        self.on_cat_change()

        frm_gem = ttk.LabelFrame(root, text='生成灵魂石（双词条 / 单词条）'); frm_gem.pack(fill='x', **pad)
        ttk.Label(frm_gem, text='主词条：').grid(row=0, column=0, sticky='e', padx=4, pady=3)
        self.gem_main = ttk.Combobox(frm_gem, state='readonly', width=58, values=self.affix_labels); self.gem_main.grid(row=0, column=1, columnspan=3, sticky='w', pady=3)
        ttk.Label(frm_gem, text='副词条：').grid(row=1, column=0, sticky='e', padx=4, pady=3)
        self.gem_sub = ttk.Combobox(frm_gem, state='readonly', width=58, values=self.sub_labels); self.gem_sub.grid(row=1, column=1, columnspan=3, sticky='w', pady=3)
        if self.affix_labels:
            self.gem_main.current(0)
            self.gem_sub.current(1 if len(self.sub_labels) > 1 else 0)
        ttk.Label(frm_gem, text='等级：').grid(row=2, column=0, sticky='e', padx=4, pady=3)
        self.gem_level = ttk.Spinbox(frm_gem, from_=1, to=5, width=5); self.gem_level.set('5'); self.gem_level.grid(row=2, column=1, sticky='w', pady=3)
        ttk.Button(frm_gem, text='生成灵魂石', command=self.make_gem).grid(row=2, column=2, sticky='w', padx=6, pady=3)

        frm_log = ttk.LabelFrame(root, text='运行日志'); frm_log.pack(fill='both', expand=True, **pad)
        self.log_txt = tk.Text(frm_log, height=12, state='disabled'); self.log_txt.pack(fill='both', expand=True, padx=4, pady=4)
        self.log_txt.tag_config('ok', foreground='#1e8e3e')
        self.log_txt.tag_config('err', foreground='#d93025')

        self.log('提示：先启动游戏进入离线单机（灵魂石功能需在营地·灵魂刻印界面），再点“连接游戏”。')
        self.log(f'词条：{len(self.affix_labels)} 条 | 可获取物品：{len(self.items)} 项')
        self.root.after(120, self.poll)
        self.root.protocol('WM_DELETE_WINDOW', self.on_close)

    def num(self, entry):
        try:
            return float(entry.get())
        except Exception:
            messagebox.showerror('输入错误', '请输入数字'); return None

    def log(self, s, tag=None):
        if tag is None:
            if s.startswith('[成功]') or s.startswith('[完成]') or s.startswith('[已连接]') or s.startswith('[Agent]'):
                tag = 'ok'
            elif s.startswith('[错误]') or s.startswith('[连接失败]') or s.startswith('[异常]') or s.startswith('[拒绝]') or s.startswith('[Frida错误]'):
                tag = 'err'
        self.log_txt.configure(state='normal')
        self.log_txt.insert('end', s + '\n', tag if tag else ())
        self.log_txt.see('end')
        self.log_txt.configure(state='disabled')

    def connect(self):
        if self.session is not None:
            self.log('已连接'); return
        try:
            dev = frida.get_local_device(); self.session = dev.attach('LostCastle2.exe')
            js = open(AGENT_PATH, encoding='utf-8').read()
            self.script = self.session.create_script(js)
            self.script.on('message', self.on_msg); self.script.load()
            self.api = self.script.exports_sync if hasattr(self.script, 'exports_sync') else self.script.exports
            self.status_var.set('已连接 LostCastle2.exe（离线单机）'); self.log('[已连接] LostCastle2.exe')
        except Exception as e:
            self.status_var.set('连接失败'); self.log('[连接失败] ' + str(e))
            if self.session:
                try: self.session.detach()
                except Exception: pass
                self.session = None

    def send(self, name, arg=None, argCode=None, argLevel=0):
        if self.api is None:
            self.log('[错误] 请先连接游戏'); return
        try:
            self.api.enqueue(name, arg, argCode, argLevel)
            self.log(f'[命令] {name} arg={arg} arg2={argCode} level={argLevel}')
        except Exception as e:
            self.log('[错误] ' + str(e))

    def res_code(self):
        sel = self.res_combo.current()
        return RES_TYPES[sel][1] if sel >= 0 else 5

    def on_res_change(self, event=None):
        if self.res_code() == 14:
            self.res_level.configure(state='normal')
        else:
            self.res_level.configure(state='disabled')

    def res_add(self):
        v = self.num(self.res_entry)
        if v is None: return
        code = self.res_code(); lv = int(self.res_level.get() or 0) if code == 14 else 0
        self.send('res', v, code, lv)

    def res_set(self):
        v = self.num(self.res_entry)
        if v is None: return
        code = self.res_code(); lv = int(self.res_level.get() or 0) if code == 14 else 0
        self.send('setres', v, code, lv)

    def on_cat_change(self, event=None):
        cat = self.cat_combo.get()
        labels = []
        self.item_map = {}
        for r in self.items:
            if r.get('cat') != cat: continue
            label = f"{r['name']} ({r['id']})"
            labels.append(label)
            self.item_map[label] = (r['id'], r['itemType'])
        self.item_combo.configure(values=labels)
        if labels:
            self.item_combo.current(0)
        else:
            self.item_combo.set('')

    def give_item(self):
        sel = self.item_map.get(self.item_combo.get())
        if not sel:
            self.log('[错误] 请选择物品'); return
        iid, itype = sel
        self.send('give', iid, itype, 1 if self.drop_var.get() else 0)

    def make_gem(self):
        if not self.affix_labels:
            self.log('[错误] 词条表缺失（gem_affix.json）'); return
        main_id = self.affix_map.get(self.gem_main.get())
        sub_id = self.sub_map.get(self.gem_sub.get())
        if main_id is None or sub_id is None:
            self.log('[错误] 请选择主/副词条'); return
        try:
            lv = int(self.gem_level.get())
        except Exception:
            lv = 5
        self.send('gem', main_id, sub_id, lv)

    def on_msg(self, message, data):
        try: self.mq.put(message)
        except Exception: pass

    def poll(self):
        try:
            while True:
                m = self.mq.get_nowait()
                if m.get('type') == 'send':
                    p = m.get('payload') or {}; tag = p.get('tag')
                    if tag == 'agent_ready':
                        self.log('[Agent] 就绪')
                    elif tag == 'done':
                        cmd = p.get('cmd'); res = p.get('res')
                        if cmd == 'gem' and isinstance(res, dict) and res.get('saved'):
                            lv = res.get('level'); sub = res.get('subType') or '无'
                            self.log(f'[成功] 灵魂石：主 {res.get("mainType")} / 副 {sub} Lv{lv}')
                        elif cmd == 'give' and isinstance(res, dict):
                            REASON = {2:'该类物品被禁止拾取',3:'堆叠上限已满',4:'无法与同类物品共存',5:'背包重量不足（已超上限）',6:'材料不足',7:'拾取失败',8:'正在交互中','already_have':'已拥有该宝藏（不能重复入包）'}
                            if res.get('ok'):
                                self.log(f'[成功] 已获取：{res.get("id")}（旧装备丢弃={res.get("discardOld")}，校验={res.get("pickupType")}）')
                            else:
                                r = res.get('reason')
                                self.log(f'[拒绝] {res.get("id")} → {REASON.get(r, res.get("error"))}')
                        else:
                            self.log(f'[完成] {cmd} => {res}')
                        if cmd == 'status' and isinstance(res, dict):
                            self.status_var.set(f'局内 | 金币 {res.get("coin")}' if res.get('inRun') else '已连接，但不在局内')
                    elif tag == 'error':
                        self.log('[异常] ' + str(p))
                elif m.get('type') == 'error':
                    self.log('[Frida错误] ' + str(m.get('description')))
        except queue.Empty:
            pass
        self.root.after(120, self.poll)

    def on_close(self):
        try:
            if self.session: self.session.detach()
        except Exception: pass
        self.root.destroy()

if __name__ == '__main__':
    root = tk.Tk(); App(root); root.mainloop()