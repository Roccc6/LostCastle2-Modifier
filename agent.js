'use strict';
function main(){
  const GA='GameAssembly.dll';
  function sym(n){return Module.getExportByName(GA,n);}
  function need(n){const a=sym(n); if(!a) throw new Error('no export '+n); return a;}
  const DOMAIN=new NativeFunction(need('il2cpp_domain_get'),'pointer',[]);
  const DOM_ASM=new NativeFunction(need('il2cpp_domain_get_assemblies'),'pointer',['pointer','pointer']);
  const ASM_IMG=new NativeFunction(need('il2cpp_assembly_get_image'),'pointer',['pointer']);
  const CLS_NAME=new NativeFunction(need('il2cpp_class_from_name'),'pointer',['pointer','pointer','pointer']);
  const CLS_METH=new NativeFunction(need('il2cpp_class_get_method_from_name'),'pointer',['pointer','pointer','int']);
  const CLS_PARENT=new NativeFunction(need('il2cpp_class_get_parent'),'pointer',['pointer']);
  const INVOKE=new NativeFunction(need('il2cpp_runtime_invoke'),'pointer',['pointer','pointer','pointer','pointer']);
  const STR_NEW=new NativeFunction(need('il2cpp_string_new'),'pointer',['pointer']);
  const UNBOX=new NativeFunction(need('il2cpp_object_unbox'),'pointer',['pointer']);
  const FMT=new NativeFunction(need('il2cpp_format_exception'),'pointer',['pointer']);
  function cstr(p){return p.isNull()?'<null>':(p.readCString()||'');}
  function findClass(ns,name){
    const domain=DOMAIN(); const sb=Memory.alloc(8); const arr=DOM_ASM(domain,sb); const n=sb.readU64().toNumber();
    for(let i=0;i<n;i++){
      const asm=arr.add(i*8).readPointer(); if(asm.isNull()) continue;
      const img=ASM_IMG(asm);
      const c=CLS_NAME(img,Memory.allocUtf8String(ns),Memory.allocUtf8String(name));
      if(!c.isNull()) return c;
    }
    return null;
  }
  function findMethod(klass,name,argc){
    let k=klass,d=0;
    while(k && !k.isNull() && d<10){
      const m=CLS_METH(k,Memory.allocUtf8String(name),argc);
      if(!m.isNull()) return m;
      k=CLS_PARENT(k); d++;
    }
    return null;
  }
  function invoke(m,obj,args){
    const exc=Memory.alloc(8); exc.writePointer(NULL);
    const r=INVOKE(m,obj,args,exc);
    const e=exc.readPointer();
    if(!e.isNull()) throw new Error('managed: '+(cstr(FMT(e))||''));
    return r;
  }
  function getBag(){
    const pmCls=findClass('LC2','PlayerManager');
    const pmgr=invoke(findMethod(pmCls,'get_Instance',0),NULL,NULL);
    if(pmgr.isNull()) return null;
    const player=invoke(CLS_METH(pmCls,Memory.allocUtf8String('get_LocalPlayer'),0),pmgr,NULL);
    if(player.isNull()) return null;
    const pCls=findClass('LC2','Player');
    const bag=invoke(CLS_METH(pCls,Memory.allocUtf8String('get_OwnBagSystem'),0),player,NULL);
    return bag.isNull()?null:bag;
  }
  function bagGetter(bag,name){
    const bCls=findClass('LC2','BagSystem');
    return UNBOX(invoke(CLS_METH(bCls,Memory.allocUtf8String(name),0),bag,NULL)).readS32();
  }
  function changeCoinOnBag(bag,delta){
    const bCls=findClass('LC2','BagSystem');
    const m=CLS_METH(bCls,Memory.allocUtf8String('ChangeCoin'),1);
    const pb=Memory.alloc(8); pb.writeFloat(Number(delta)||0);
    const arr=Memory.alloc(8); arr.writePointer(pb);
    invoke(m,bag,arr);
  }
  const getterByCode={4:'get_Crystal',7:'get_IronPowder',5:'get_Coin',60:'get_UnLockActiveProp'};
  function cmd_coin(delta){
    const bag=getBag(); if(!bag) return {error:'no local bag (need be in a run)'};
    const before=bagGetter(bag,'get_Coin');
    changeCoinOnBag(bag,delta);
    return {before:before,after:bagGetter(bag,'get_Coin'),delta:Number(delta)||0};
  }
  function cmd_setcoin(target){
    const bag=getBag(); if(!bag) return {error:'no local bag'};
    const before=bagGetter(bag,'get_Coin');
    changeCoinOnBag(bag,Number(target)-before);
    return {before:before,after:bagGetter(bag,'get_Coin'),target:Number(target)||0};
  }
  function cmd_unlockprop(delta){
    const bag=getBag(); if(!bag) return {error:'no local bag'};
    const before=bagGetter(bag,'get_UnLockActiveProp');
    const bCls=findClass('LC2','BagSystem');
    const m=CLS_METH(bCls,Memory.allocUtf8String('ChangeUnLockActiveProp'),1);
    const pb=Memory.alloc(8); pb.writeFloat(Number(delta)||0);
    const arr=Memory.alloc(8); arr.writePointer(pb);
    invoke(m,bag,arr);
    return {before:before,after:bagGetter(bag,'get_UnLockActiveProp'),delta:Number(delta)||0};
  }
  function cmd_value(code,amount,level){
    const bag=getBag(); if(!bag) return {error:'no local bag'};
    const bCls=findClass('LC2','BagSystem');
    const getter=getterByCode[code]||null;
    const before=getter?bagGetter(bag,getter):null;
    const m=CLS_METH(bCls,Memory.allocUtf8String('ChangeValueItem'),4);
    const arr=Memory.alloc(8*4);
    const b0=Memory.alloc(8); b0.writeS32(code); arr.writePointer(b0);
    const b1=Memory.alloc(8); b1.writeS32(Number(amount)||0); arr.add(8).writePointer(b1);
    const b2=Memory.alloc(8); b2.writeU8(1); arr.add(16).writePointer(b2);
    const b3=Memory.alloc(8); b3.writeS32(level||0); arr.add(24).writePointer(b3);
    invoke(m,bag,arr);
    return {code:code,amount:Number(amount)||0,before:before,after:getter?bagGetter(bag,getter):null};
  }
  function cmd_gem(mainType,subType,level){
    const gemCls=findClass('LC2','Gem');
    if(!gemCls) return {error:'Gem class not found'};
    const m=CLS_METH(gemCls,Memory.allocUtf8String('GenerateNewGemAndSaveIntoPlayerData'),4);
    if(m.isNull()) return {error:'factory method not found'};
    const sMain=STR_NEW(Memory.allocUtf8String(String(mainType)));
    const sSub=STR_NEW(Memory.allocUtf8String(String(subType)));
    const lv=parseInt(level)||5;
    const arr=Memory.alloc(8*4);
    arr.writePointer(sMain);
    const p1=Memory.alloc(8); p1.writeS32(lv); arr.add(8).writePointer(p1);
    arr.add(16).writePointer(sSub);
    const p3=Memory.alloc(8); p3.writeS32(lv); arr.add(24).writePointer(p3);
    const gem=invoke(m,NULL,arr);
    if(gem.isNull()) return {error:'factory returned null',mainType:mainType,subType:subType};
    let saved=false;
    try{
      const mgrCls=findClass('LC2','InscriptionMgr');
      const mgr=invoke(findMethod(mgrCls,'get_Instance',0),NULL,NULL);
      if(!mgr.isNull()){
        const saveData=mgr.add(0x18).readPointer();
        if(!saveData.isNull()){
          const saveCls=findClass('LC2','InscriptionMgrSaveData');
          invoke(findMethod(saveCls,'SaveToSaveData',0),saveData,NULL);
          const gsCls=findClass('LC2','GameSaveDataMgr');
          const gs=invoke(findMethod(gsCls,'get_Instance',0),NULL,NULL);
          invoke(findMethod(gsCls,'SaveCurGameSaveDataImmediate',0),gs,NULL);
          saved=true;
        }
      }
    }catch(e){ return {error:'save failed: '+String(e),gem:gem.toString(),mainType:mainType,subType:subType}; }
    return {gem:gem.toString(),mainType:mainType,subType:subType,level:lv,saved:saved};
  }
  function resGetter(code,level){
    const bag=getBag(); if(!bag) return null;
    const bCls=findClass('LC2','BagSystem');
    if(code===14){
      const m=CLS_METH(bCls,Memory.allocUtf8String('SoulFlower'),1);
      const arr=Memory.alloc(8); const pl=Memory.alloc(8); pl.writeS32(level||0); arr.writePointer(pl);
      return UNBOX(invoke(m,bag,arr)).readS32();
    }
    const name=getterByCode[code];
    return name?bagGetter(bag,name):null;
  }
  function resChange(code,delta,level){
    const bag=getBag(); if(!bag) return false;
    const bCls=findClass('LC2','BagSystem');
    if(code===5){ changeCoinOnBag(bag,delta); return true; }
    if(code===60){
      const m=CLS_METH(bCls,Memory.allocUtf8String('ChangeUnLockActiveProp'),1);
      const pb=Memory.alloc(8); pb.writeFloat(Number(delta)||0);
      const arr=Memory.alloc(8); arr.writePointer(pb);
      invoke(m,bag,arr); return true;
    }
    if(code===14){
      const m=CLS_METH(bCls,Memory.allocUtf8String('ChangeSoulFlower'),2);
      const arr=Memory.alloc(16);
      const pl=Memory.alloc(8); pl.writeS32(level||0); arr.writePointer(pl);
      const pd=Memory.alloc(8); pd.writeFloat(Number(delta)||0); arr.add(8).writePointer(pd);
      invoke(m,bag,arr); return true;
    }
    const m=CLS_METH(bCls,Memory.allocUtf8String('ChangeValueItem'),4);
    const arr=Memory.alloc(8*4);
    const b0=Memory.alloc(8); b0.writeS32(code); arr.writePointer(b0);
    const b1=Memory.alloc(8); b1.writeS32(Number(delta)||0); arr.add(8).writePointer(b1);
    const b2=Memory.alloc(8); b2.writeU8(1); arr.add(16).writePointer(b2);
    const b3=Memory.alloc(8); b3.writeS32(level||0); arr.add(24).writePointer(b3);
    invoke(m,bag,arr); return true;
  }
  function cmd_res(code,delta,level){
    const before=resGetter(code,level);
    if(before===null) return {error:'no local bag (need be in a run)'};
    if(!resChange(code,delta,level)) return {error:'change failed'};
    return {code:code,before:before,after:resGetter(code,level),delta:Number(delta)||0,level:level||0};
  }
  function cmd_setres(code,target,level){
    const before=resGetter(code,level);
    if(before===null) return {error:'no local bag (need be in a run)'};
    resChange(code,Number(target)-before,level);
    return {code:code,before:before,after:resGetter(code,level),target:Number(target)||0,level:level||0};
  }
  function getLocalPlayer(){
    const pmCls=findClass('LC2','PlayerManager');
    const pmgr=invoke(findMethod(pmCls,'get_Instance',0),NULL,NULL);
    return invoke(CLS_METH(pmCls,Memory.allocUtf8String('get_LocalPlayer'),0),pmgr,NULL);
  }
  function cmd_give(id,itemType,discard){
    const edCls=findClass('LC2','EntityDataAssetMgr');
    const ed=invoke(findMethod(edCls,'get_Instance',0),NULL,NULL);
    const mData=CLS_METH(edCls,Memory.allocUtf8String('GetItemDataByID'),1);
    const a1=Memory.alloc(8); a1.writePointer(STR_NEW(Memory.allocUtf8String(String(id))));
    const data=invoke(mData,ed,a1);
    if(data.isNull()) return {error:'item data not found: '+id};
    const bag=getBag(); if(!bag) return {error:'no local bag'};
    const player=getLocalPlayer(); if(player.isNull()) return {error:'no local player'};
    let xf=NULL;
    try{
      const compCls=findClass('UnityEngine','Component');
      const mT=CLS_METH(compCls,Memory.allocUtf8String('get_transform'),0);
      xf=invoke(mT,player,NULL);
    }catch(e){}
    const imCls=findClass('LC2','ItemMgr');
    const im=invoke(findMethod(imCls,'get_Instance',0),NULL,NULL);
    const mCreate=CLS_METH(imCls,Memory.allocUtf8String('CreateItemObject'),5);
    const arr=Memory.alloc(8*5);
    arr.writePointer(data);
    const vec=Memory.alloc(16); vec.writeFloat(0); vec.add(4).writeFloat(0); vec.add(8).writeFloat(0); arr.add(8).writePointer(vec);
    arr.add(16).writePointer(xf);
    const ot=Memory.alloc(8); ot.writeS32(1); arr.add(24).writePointer(ot);
    const pidb=Memory.alloc(8); pidb.writeU64(0); arr.add(32).writePointer(pidb);
    const item=invoke(mCreate,im,arr);
    if(item.isNull()) return {error:'create item failed'};
    const bCls=findClass('LC2','BagSystem');
    const REASON={0:'ok',1:'wait_dropping',2:'banned',3:'not_enough_max_stack',4:'not_same_item',5:'not_enough_weight',6:'not_enough_crystal',7:'failed',8:'interacting'};
    if(Number(itemType)===3){
      try{
        const mNum=CLS_METH(bCls,Memory.allocUtf8String('CheckItemNum'),2);
        const na=Memory.alloc(16);
        const n1=Memory.alloc(8); n1.writeS32(3); na.writePointer(n1);
        na.add(8).writePointer(STR_NEW(Memory.allocUtf8String(String(id))));
        const nexc=Memory.alloc(8); nexc.writePointer(NULL);
        const nRet=INVOKE(mNum,bag,na,nexc);
        const have=nexc.readPointer().isNull()?UNBOX(nRet).readS32():0;
        if(have>0){
          try{
            const mDel0=CLS_METH(imCls,Memory.allocUtf8String('DestroyItem'),1);
            const da0=Memory.alloc(8); da0.writePointer(item);
            invoke(mDel0,im,da0);
          }catch(e){}
          return {error:'already have this treasure',reason:'already_have',id:id,have:have};
        }
      }catch(e){}
    }
    const mType=Number(itemType)===3?CLS_METH(bCls,Memory.allocUtf8String('GetPickUpType_PassiveProps'),1):CLS_METH(bCls,Memory.allocUtf8String('GetPickUpType'),1);
    const ta=Memory.alloc(8); ta.writePointer(item);
    const tExc=Memory.alloc(8); tExc.writePointer(NULL);
    const tRet=INVOKE(mType,bag,ta,tExc);
    let ptype=-1;
    try{ ptype=UNBOX(tRet).readS32(); }catch(e){ ptype=-1; }
    if(ptype!==0 && ptype!==1){
      try{
        const mDel=CLS_METH(imCls,Memory.allocUtf8String('DestroyItem'),1);
        const da=Memory.alloc(8); da.writePointer(item);
        invoke(mDel,im,da);
      }catch(e){}
      return {error:'cannot pickup: '+(REASON[ptype]||ptype),reason:ptype,id:id};
    }
    const mPick=CLS_METH(bCls,Memory.allocUtf8String('PickUp'),3);
    const p2=Memory.alloc(8*3);
    p2.writePointer(item);
    const pb1=Memory.alloc(8); pb1.writeU8(discard?1:0); p2.add(8).writePointer(pb1);
    const pb2=Memory.alloc(8); pb2.writeU8(1); p2.add(16).writePointer(pb2);
    invoke(mPick,bag,p2);
    return {id:id,itemType:Number(itemType)||0,discardOld:!!discard,pickupType:ptype,ok:true};
  }
  function cmd_status(){
    const bag=getBag();
    return {inRun:!!bag, coin:bag?bagGetter(bag,'get_Coin'):null};
  }
  function process(task){
    try{
      let res;
      const cmd=String(task.cmd);
      if(cmd==='coin') res=cmd_coin(task.arg);
      else if(cmd==='setcoin') res=cmd_setcoin(task.arg);
      else if(cmd==='value') res=cmd_value(Number(task.argCode)||0,task.arg,Number(task.argLevel)||0);
      else if(cmd==='unlockprop') res=cmd_unlockprop(task.arg);
      else if(cmd==='res') res=cmd_res(Number(task.argCode)||0,task.arg,Number(task.argLevel)||0);
      else if(cmd==='setres') res=cmd_setres(Number(task.argCode)||0,task.arg,Number(task.argLevel)||0);
      else if(cmd==='give') res=cmd_give(task.arg,Number(task.argCode)||0,Number(task.argLevel)||0);
      else if(cmd==='gem') res=cmd_gem(task.arg,task.argCode,Number(task.argLevel)||5);
      else if(cmd==='status') res=cmd_status();
      else res={error:'unknown cmd '+cmd};
      send({tag:'done',cmd:cmd,res:res});
    }catch(e){
      send({tag:'error',cmd:String(task.cmd),msg:String(e)});
    }
  }
  const mod=Process.findModuleByName(GA);
  const updateAddr=mod.base.add(0x578C220);
  const queue=[];
  Interceptor.attach(updateAddr,{onEnter(){
    while(queue.length){ const t=queue.shift(); process(t); }
  }});
  send({tag:'agent_ready'});
  rpc.exports={
    enqueue:function(cmd,arg,argCode,argLevel){
      queue.push({cmd:String(cmd),arg:arg,argCode:argCode,argLevel:argLevel});
      return queue.length;
    }
  };
}
main();