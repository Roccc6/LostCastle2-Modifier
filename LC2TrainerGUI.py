import tkinter as tk
from tkinter import ttk, messagebox
import frida, queue, os, json

BASE = os.path.dirname(os.path.abspath(__file__))
AGENT_PATH = os.path.join(BASE, 'agent.js')
AFFIX_PATH = os.path.join(BASE, 'gem_affix.json')
ITEMS_PATH = os.path.join(BASE, 'items_give.json')

BG, PANEL, INPUT, BORDER = '#15171c', '#1e2128', '#262a33', '#333945'
TEXT, MUTED, DESC = '#e8eaed', '#9aa4b2', '#c3ccd8'
ACCENT, OK, ERR, WARN = '#4c8dff', '#3ddc84', '#ff5c5c', '#f5c26b'
FONT = ('Microsoft YaHei UI', 10)
FONT_SM = ('Microsoft YaHei UI', 9)
FONT_BOLD = ('Microsoft YaHei UI', 10, 'bold')
FONT_TITLE = ('Microsoft YaHei UI', 15, 'bold')

RES_TYPES = [('金币', 5), ('魂晶碎片', 4), ('魔铁锭', 7), ('黑铁原石', 60), ('魂花', 14)]
CATS = ['武器', '防具', '被动宝藏', '主动道具', '消耗品']

def setup_style(root):
    st = ttk.Style(root)
    try: st.theme_use('clam')
    except Exception: pass
    st.configure('.', background=PANEL, foreground=TEXT, fieldbackground=INPUT, font=FONT)
    st.configure('TFrame', background=PANEL)
    st.configure('BG.TFrame', background=BG)
    st.configure('TLabel', background=PANEL, foreground=TEXT, font=FONT)
    st.configure('Muted.TLabel', background=PANEL, foreground=MUTED, font=FONT_SM)
    st.configure('Title.TLabel', background=BG, foreground=TEXT, font=FONT_TITLE)
    st.configure('Sub.TLabel', background=BG, foreground=MUTED, font=FONT_SM)
    st.configure('Warn.TLabel', background=BG, foreground=WARN, font=FONT)
    st.configure('Online.TLabel', background=BG, foreground=OK, font=FONT_BOLD)
    st.configure('Card.TLabelframe', background=PANEL, bordercolor=BORDER, relief='solid', borderwidth=1)
    st.configure('Card.TLabelframe.Label', background=PANEL, foreground=ACCENT, font=FONT_BOLD)
    st.configure('TButton', background=INPUT, foreground=TEXT, bordercolor=BORDER, padding=(10, 5), font=FONT, relief='flat')
    st.map('TButton', background=[('active', '#2f3542'), ('pressed', '#3a4252')], foreground=[('disabled', MUTED)])
    st.configure('Accent.TButton', background=ACCENT, foreground='#0b0f14', font=FONT_BOLD)
    st.map('Accent.TButton', background=[('active', '#6aa3ff'), ('pressed', '#3a7ae6')])
    st.configure('TEntry', fieldbackground=INPUT, foreground=TEXT, insertcolor=TEXT, bordercolor=BORDER, padding=4)
    st.configure('TCombobox', fieldbackground=INPUT, background=INPUT, foreground=TEXT, arrowcolor=TEXT, bordercolor=BORDER, padding=3)
    st.map('TCombobox', fieldbackground=[('readonly', INPUT)], foreground=[('readonly', TEXT)], background=[('readonly', INPUT)])
    st.configure('TSpinbox', fieldbackground=INPUT, foreground=TEXT, arrowcolor=TEXT, bordercolor=BORDER, padding=4)
    st.configure('TCheckbutton', background=PANEL, foreground=TEXT, font=FONT)
    st.map('TCheckbutton', background=[('active', PANEL)])
    root.option_add('*TCombobox*Listbox.background', INPUT)
    root.option_add('*TCombobox*Listbox.foreground', TEXT)
    root.option_add('*TCombobox*Listbox.selectBackground', ACCENT)
    root.option_add('*TCombobox*Listbox.selectForeground', '#0b0f14')
    root.option_add('*TCombobox*Listbox.font', FONT_SM)

def load_json(path, default):
    try:
        return json.load(open(path, encoding='utf-8'))
    except Exception:
        return default

class App:
    def __init__(self, root):
        self.root = root
        root.title('失落城堡2 修改器')
        root.configure(bg=BG)
        root.geometry('1160x760')
        root.minsize(1000, 660)
        self.session = None; self.script = None; self.api = None
        self.mq = queue.Queue()

        rows = load_json(AFFIX_PATH, [])
        def lb(r): return f"[{r['slot']}|{r['rare']}] {r['name']} ({r['id']})"
        self.affix_labels = [lb(r) for r in rows]
        self.affix_map = {lb(r): r['id'] for r in rows}
        self.affix_row = {lb(r): r for r in rows}
        self.sub_labels = ['【无】仅主词条（单词条石头）'] + self.affix_labels
        self.sub_map = {'【无】仅主词条（单词条石头）': ''}
        self.sub_map.update(self.affix_map)
        self.items = load_json(ITEMS_PATH, [])
        self.item_map = {}

        header = ttk.Frame(root, style='BG.TFrame')
        header.grid(row=0, column=0, columnspan=2, sticky='ew', padx=16, pady=(14, 4))
        ttk.Label(header, text='失落城堡2 修改器', style='Title.TLabel').pack(side='left')
        ttk.Label(header, text='   离线单机 · 资源 / 装备 / 灵魂石', style='Sub.TLabel').pack(side='left', pady=(6, 0))
        btns = ttk.Frame(header, style='BG.TFrame'); btns.pack(side='right')
        ttk.Button(btns, text='连接游戏', style='Accent.TButton', command=self.connect).pack(side='right')
        ttk.Button(btns, text='刷新状态', command=lambda: self.send('status')).pack(side='right', padx=8)

        self.status_var = tk.StringVar(value='未连接（请先启动游戏并进入离线单机）')
        self.status_lbl = ttk.Label(root, textvariable=self.status_var, style='Warn.TLabel')
        self.status_lbl.grid(row=1, column=0, columnspan=2, sticky='w', padx=18, pady=(0, 6))

        left = ttk.Frame(root); left.grid(row=2, column=0, sticky='nsew', padx=(16, 8), pady=(4, 14))
        right = ttk.Frame(root); right.grid(row=2, column=1, sticky='nsew', padx=(8, 16), pady=(4, 14))
        root.columnconfigure(0, weight=0); root.columnconfigure(1, weight=1)
        root.rowconfigure(2, weight=1)

        # 资源
        frm_res = ttk.LabelFrame(left, text=' 资源 / 货币（当前局） ', style='Card.TLabelframe')
        frm_res.pack(fill='x', pady=(0, 10), ipadx=8, ipady=6)
        ttk.Label(frm_res, text='类型').grid(row=0, column=0, sticky='e', padx=(6, 6), pady=6)
        self.res_combo = ttk.Combobox(frm_res, state='readonly', width=14, values=[n for n, c in RES_TYPES])
        self.res_combo.current(0); self.res_combo.grid(row=0, column=1, sticky='w', pady=6)
        self.res_combo.bind('<<ComboboxSelected>>', self.on_res_change)
        ttk.Label(frm_res, text='数量').grid(row=0, column=2, sticky='e', padx=(14, 6), pady=6)
        self.res_entry = ttk.Entry(frm_res, width=12); self.res_entry.grid(row=0, column=3, sticky='w', pady=6)
        self.res_entry.insert(0, '1000')
        ttk.Label(frm_res, text='等级').grid(row=1, column=0, sticky='e', padx=(6, 6), pady=6)
        self.res_level = ttk.Spinbox(frm_res, from_=0, to=6, width=5); self.res_level.set('0')
        self.res_level.grid(row=1, column=1, sticky='w', pady=6)
        ttk.Button(frm_res, text='增加', style='Accent.TButton', command=self.res_add).grid(row=0, column=4, padx=10, sticky='ew')
        ttk.Button(frm_res, text='设为', command=self.res_set).grid(row=1, column=4, padx=10, sticky='ew')
        self.on_res_change()

        # 物品
        frm_item = ttk.LabelFrame(left, text=' 获取装备 / 宝藏（直接进包） ', style='Card.TLabelframe')
        frm_item.pack(fill='x', pady=(0, 10), ipadx=8, ipady=6)
        ttk.Label(frm_item, text='分类').grid(row=0, column=0, sticky='e', padx=(6, 6), pady=6)
        self.cat_combo = ttk.Combobox(frm_item, state='readonly', width=12, values=CATS)
        self.cat_combo.current(0); self.cat_combo.grid(row=0, column=1, sticky='w', pady=6)
        self.cat_combo.bind('<<ComboboxSelected>>', self.on_cat_change)
        ttk.Label(frm_item, text='物品').grid(row=1, column=0, sticky='e', padx=(6, 6), pady=6)
        self.item_combo = ttk.Combobox(frm_item, state='readonly', width=54)
        self.item_combo.grid(row=1, column=1, columnspan=3, sticky='we', pady=6)
        self.drop_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frm_item, text='旧装备丢到地上', variable=self.drop_var).grid(row=2, column=1, sticky='w', pady=6)
        ttk.Button(frm_item, text='获取', style='Accent.TButton', command=self.give_item).grid(row=2, column=3, sticky='e', padx=10)
        frm_item.columnconfigure(1, weight=1)
        self.on_cat_change()

        # 灵魂石 + 预览
        frm_gem = ttk.LabelFrame(left, text=' 生成灵魂石 ', style='Card.TLabelframe')
        frm_gem.pack(fill='x', pady=(0, 10), ipadx=8, ipady=6)
        ttk.Label(frm_gem, text='主词条').grid(row=0, column=0, sticky='e', padx=(6, 6), pady=6)
        self.gem_main = ttk.Combobox(frm_gem, state='readonly', width=54, values=self.affix_labels)
        self.gem_main.grid(row=0, column=1, columnspan=3, sticky='we', pady=6)
        ttk.Label(frm_gem, text='副词条').grid(row=1, column=0, sticky='e', padx=(6, 6), pady=6)
        self.gem_sub = ttk.Combobox(frm_gem, state='readonly', width=54, values=self.sub_labels)
        self.gem_sub.grid(row=1, column=1, columnspan=3, sticky='we', pady=6)
        ttk.Label(frm_gem, text='等级').grid(row=2, column=0, sticky='e', padx=(6, 6), pady=6)
        self.gem_level_var = tk.StringVar(value='5')
        self.gem_level = ttk.Spinbox(frm_gem, from_=1, to=5, width=5, textvariable=self.gem_level_var)
        self.gem_level.grid(row=2, column=1, sticky='w', pady=6)
        ttk.Button(frm_gem, text='生成灵魂石', style='Accent.TButton', command=self.make_gem).grid(row=2, column=3, sticky='e', padx=10)
        frm_gem.columnconfigure(1, weight=1)
        self.gem_main.bind('<<ComboboxSelected>>', self.update_preview)
        self.gem_sub.bind('<<ComboboxSelected>>', self.update_preview)
        self.gem_level_var.trace_add('write', lambda *a: self.update_preview())

        if self.affix_labels:
            self.gem_main.current(0)
            self.gem_sub.current(1 if len(self.sub_labels) > 1 else 0)
        self.update_preview()

        # 石头预览
        frm_prev = ttk.LabelFrame(right, text=' 石头预览 ', style='Card.TLabelframe')
        frm_prev.pack(fill='x', pady=(0, 10), ipadx=6, ipady=6)
        self.preview = tk.Text(frm_prev, height=12, state='disabled', bg='#12141a', fg=DESC,
                               relief='flat', borderwidth=0, font=FONT_SM, wrap='word', padx=10, pady=8)
        self.preview.pack(fill='both', expand=True, padx=4, pady=4)
        self.preview.tag_config('head', foreground=ACCENT, font=FONT_BOLD)
        self.preview.tag_config('warn', foreground=WARN)

        # 日志
        frm_log = ttk.LabelFrame(right, text=' 运行日志 ', style='Card.TLabelframe')
        frm_log.pack(fill='both', expand=True, ipadx=6, ipady=6)
        self.log_txt = tk.Text(frm_log, height=24, state='disabled', bg='#0f1115', fg=TEXT,
                               insertbackground=TEXT, relief='flat', borderwidth=0,
                               font=FONT_SM, wrap='word', padx=10, pady=8)
        self.log_txt.pack(fill='both', expand=True)
        self.log_txt.tag_config('ok', foreground=OK)
        self.log_txt.tag_config('err', foreground=ERR)
        ttk.Label(right, style='Muted.TLabel',
                  text='提示：需先进入离线单机；灵魂石功能请先在营地打开“灵魂刻印”界面。').pack(anchor='w', pady=(6, 0))

        self.log('欢迎使用。点击右上角「连接游戏」开始。')
        self.log(f'已加载：灵魂石词条 {len(self.affix_labels)} 条（含作用说明），可获取物品 {len(self.items)} 项')
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
            self.status_var.set('已连接 LostCastle2.exe（离线单机）')
            self.status_lbl.configure(style='Online.TLabel')
            self.log('[已连接] LostCastle2.exe')
        except Exception as e:
            self.status_var.set('连接失败：请确认游戏已启动')
            self.status_lbl.configure(style='Warn.TLabel')
            self.log('[连接失败] ' + str(e))
            if self.session:
                try: self.session.detach()
                except Exception: pass
                self.session = None

    def send(self, name, arg=None, argCode=None, argLevel=0):
        if self.api is None:
            self.log('[错误] 请先连接游戏'); return
        try:
            self.api.enqueue(name, arg, argCode, argLevel)
            self.log(f'[命令] {name} {arg if arg is not None else ""} {argCode if argCode is not None else ""} {argLevel}')
        except Exception as e:
            self.log('[错误] ' + str(e))

    def res_code(self):
        sel = self.res_combo.current()
        return RES_TYPES[sel][1] if sel >= 0 else 5

    def on_res_change(self, event=None):
        self.res_level.configure(state='normal' if self.res_code() == 14 else 'disabled')

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
        labels = []; self.item_map = {}
        for r in self.items:
            if r.get('cat') != cat: continue
            L = f"{r['name']} ({r['id']})"
            labels.append(L); self.item_map[L] = (r['id'], r['itemType'])
        self.item_combo.configure(values=labels)
        self.item_combo.set(labels[0] if labels else '')

    def give_item(self):
        sel = self.item_map.get(self.item_combo.get())
        if not sel:
            self.log('[错误] 请选择物品'); return
        iid, itype = sel
        self.send('give', iid, itype, 1 if self.drop_var.get() else 0)

    # ------- 石头预览 -------
    def update_preview(self, event=None):
        if not hasattr(self, 'preview'):
            return
        m = self.affix_row.get(self.gem_main.get())
        sub_label = self.gem_sub.get()
        s = None if sub_label.startswith('【无】') else self.affix_row.get(sub_label)
        try: lv = int(self.gem_level_var.get())
        except Exception: lv = 5

        self.preview.configure(state='normal')
        self.preview.delete('1.0', 'end')
        if not m:
            self.preview.insert('end', '请选择主词条', 'warn')
            self.preview.configure(state='disabled'); return

        count = '2（双词条）' if s else '1（单词条）'
        self.preview.insert('end', '形状  ', 'head'); self.preview.insert('end', f"{m['slot']}（由主词条决定）\n")
        self.preview.insert('end', '类型  ', 'head'); self.preview.insert('end', f"{m['rare']} 级   等级 Lv{lv}   词条数 {count}\n\n")

        self.preview.insert('end', '主词条  ', 'head')
        self.preview.insert('end', f"{m['name']}  [{m['id']}]  上限 Lv{m['maxLevel']}  限制 {m['weapon']}\n")
        self.preview.insert('end', f"        {m.get('desc','') or '—'}\n", 'warn' if not m.get('desc') else '')

        if s:
            self.preview.insert('end', '\n副词条  ', 'head')
            self.preview.insert('end', f"{s['name']}  [{s['id']}]  上限 Lv{s['maxLevel']}  限制 {s['weapon']}\n")
            self.preview.insert('end', f"        {s.get('desc','') or '—'}\n")
        else:
            self.preview.insert('end', '\n副词条  ', 'head'); self.preview.insert('end', '无（单词条石头）\n')

        # 冲突提示
        warns = []
        mw, sw = m.get('weapon',''), (s or {}).get('weapon','')
        if mw != '全武器':
            warns.append(f'主词条限用于「{mw}」，该石头只能给对应武器使用')
        if s and sw and sw != '全武器' and mw != '全武器' and sw != mw:
            warns.append(f'主/副词条武器限制不同（{mw} / {sw}），可能无法同时生效')
        if lv > m['maxLevel']:
            warns.append(f'等级超过主词条上限 Lv{m["maxLevel"]}，游戏可能拒绝')
        if s and lv > s['maxLevel']:
            warns.append(f'等级超过副词条上限 Lv{s["maxLevel"]}，游戏可能拒绝')
        if warns:
            self.preview.insert('end', '\n提示\n', 'head')
            for w in warns:
                self.preview.insert('end', '· ' + w + '\n', 'warn')
        self.preview.configure(state='disabled')

    def make_gem(self):
        if not self.affix_labels:
            self.log('[错误] 词条表缺失（gem_affix.json）'); return
        main_id = self.affix_map.get(self.gem_main.get())
        sub_id = self.sub_map.get(self.gem_sub.get())
        if main_id is None or sub_id is None:
            self.log('[错误] 请选择主/副词条'); return
        try: lv = int(self.gem_level_var.get())
        except Exception: lv = 5
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
                            REASON = {2:'该类物品被禁止拾取',3:'堆叠上限已满',4:'无法与同类物品共存',
                                      5:'背包重量不足（已超上限）',6:'材料不足',7:'拾取失败',8:'正在交互中',
                                      'already_have':'已拥有该宝藏（不能重复入包）'}
                            if res.get('ok'):
                                self.log(f'[成功] 已获取：{res.get("id")}（旧装备丢弃={res.get("discardOld")}，校验={res.get("pickupType")}）')
                            else:
                                r = res.get('reason')
                                self.log(f'[拒绝] {res.get("id")} → {REASON.get(r, res.get("error"))}')
                        else:
                            self.log(f'[完成] {cmd} => {res}')
                        if cmd == 'status' and isinstance(res, dict):
                            if res.get('inRun'):
                                self.status_var.set(f'局内 · 金币 {res.get("coin")}')
                            else:
                                self.status_var.set('已连接，但不在局内（无角色背包）')
                            self.status_lbl.configure(style='Online.TLabel')
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
    root = tk.Tk()
    setup_style(root)
    App(root)
    root.mainloop()