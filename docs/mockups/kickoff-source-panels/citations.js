(() => {
  const regions = [...document.querySelectorAll('.citation-region')];
  const modeButtons = [...document.querySelectorAll('[data-mode]')];
  const sourceToggle = document.getElementById('sources-toggle');
  const modeCaption = document.getElementById('mode-caption');
  let frame;
  const isMobile = () => matchMedia('(max-width:760px)').matches;
  function layout() {
    cancelAnimationFrame(frame);
    frame = requestAnimationFrame(() => {
      for (const region of regions) {
        const rect = region.getBoundingClientRect();
        let previousBottom=100;
        let neededHeight=0;
        const margin=document.body.dataset.citationMode==='margin';
        region.querySelectorAll('.source-note').forEach(note => {
          const anchor=region.querySelector(note.dataset.anchor);
          if(!anchor)return;
          const y=Math.max(100,anchor.getBoundingClientRect().top-rect.top,previousBottom);
          note.style.setProperty('--source-top',`${Math.round(y)}px`);
          const panel=note.querySelector('.source-panel');
          const height=note.open ? note.querySelector(':scope > summary').offsetHeight+panel.offsetHeight+8 : note.querySelector(':scope > summary').offsetHeight;
          previousBottom=y+(margin?height:42)+10;
          neededHeight=Math.max(neededHeight,y+height+28);
        });
        region.style.setProperty('--source-min-height',isMobile()?'0px':`${Math.ceil(neededHeight)}px`);
      }
    });
  }
  function refreshHighlights() {
    regions.forEach(region=>{
      region.querySelectorAll('.citation-highlight').forEach(el=>el.classList.remove('citation-highlight'));
      if(!document.body.classList.contains('citations-hidden'))region.querySelectorAll('.source-note[open]').forEach(note=>region.querySelector(note.dataset.anchor)?.classList.add('citation-highlight'));
    });
  }
  function setMode(mode) {
    const safeMode=mode==='margin'?'margin':'floating';
    document.body.dataset.citationMode=safeMode;
    modeButtons.forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.mode===safeMode)));
    modeCaption.textContent=safeMode==='margin'?'Margin notes · Evidence makes room beside the section, keeping both visible.':'Floating notes · Evidence opens over the right edge without resizing the section.';
    const url=new URL(location.href);url.searchParams.set('mode',safeMode);history.replaceState(null,'',url);
    layout();
  }
  modeButtons.forEach(button=>button.addEventListener('click',()=>setMode(button.dataset.mode)));
  regions.forEach(region=>{
    region.querySelectorAll('.source-note').forEach(note=>{
      note.addEventListener('toggle',()=>{
        if(note.open){
          region.querySelectorAll('.source-note[open]').forEach(other=>{if(other!==note)other.open=false;});
          const summary=note.querySelector(':scope > summary');
          summary.setAttribute('aria-expanded','true');
        }else note.querySelector(':scope > summary').setAttribute('aria-expanded','false');
        refreshHighlights();layout();
      });
      note.querySelector('.source-close').addEventListener('click',()=>{note.open=false;note.querySelector(':scope > summary').focus();});
    });
  });
  sourceToggle.addEventListener('click',()=>{
    const hidden=document.body.classList.toggle('citations-hidden');
    sourceToggle.setAttribute('aria-pressed',String(!hidden));
    sourceToggle.textContent=hidden?'Sources off':'Sources on';
    refreshHighlights();layout();
  });
  document.addEventListener('keydown',event=>{
    if(event.key!=='Escape')return;
    const active=document.activeElement.closest('.source-note') ?? [...document.querySelectorAll('.source-note[open]')].find(note=>{const r=note.getBoundingClientRect();return r.top<innerHeight&&r.bottom>0;});
    if(active?.open){active.open=false;active.querySelector(':scope > summary').focus();}
  });
  document.documentElement.classList.add('citations-ready');
  setMode(new URL(location.href).searchParams.get('mode'));
  const observer=new ResizeObserver(layout);
  regions.forEach(region=>{observer.observe(region.querySelector('.citation-content'));region.querySelectorAll('.source-panel').forEach(panel=>observer.observe(panel));});
  window.addEventListener('resize',layout);
  window.addEventListener('scroll',layout,{passive:true});
  document.fonts.ready.then(layout);
  window.addEventListener('load',layout);
})();
