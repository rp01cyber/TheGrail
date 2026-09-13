// Lightweight Markdown editor: toolbar inserts Markdown; preview uses the
// server's own renderer so it matches the published page exactly. No deps.
(function(){
  function surround(ta, before, after, placeholder){
    const s=ta.selectionStart, e=ta.selectionEnd, v=ta.value;
    const sel=v.slice(s,e) || placeholder || "";
    ta.value=v.slice(0,s)+before+sel+after+v.slice(e);
    ta.focus();
    ta.selectionStart=s+before.length;
    ta.selectionEnd=s+before.length+sel.length;
  }
  function linePrefix(ta, prefix){
    const s=ta.selectionStart, v=ta.value;
    const lineStart=v.lastIndexOf("\n",s-1)+1;
    ta.value=v.slice(0,lineStart)+prefix+v.slice(lineStart);
    ta.focus(); ta.selectionStart=ta.selectionEnd=s+prefix.length;
  }
  const actions={
    bold:t=>surround(t,"**","**","bold text"),
    italic:t=>surround(t,"*","*","italic text"),
    code:t=>surround(t,"`","`","code"),
    codeblock:t=>surround(t,"\n```bash\n","\n```\n","command here"),
    h2:t=>linePrefix(t,"## "),
    h3:t=>linePrefix(t,"### "),
    ul:t=>linePrefix(t,"- "),
    ol:t=>linePrefix(t,"1. "),
    quote:t=>linePrefix(t,"> "),
    link:t=>surround(t,"[","](https://)","label"),
    table:t=>surround(t,"\n| Col A | Col B |\n|---|---|\n| a | b |\n","","")
  };
  document.querySelectorAll(".toolbar").forEach(bar=>{
    const pane=bar.closest(".editor-pane");
    const ta=pane.querySelector(".md-area");
    bar.querySelectorAll(".tb[data-act]").forEach(btn=>{
      btn.addEventListener("click",e=>{e.preventDefault();actions[btn.dataset.act](ta);});
    });
    const pvBtn=bar.querySelector(".tb-preview");
    const box=pane.querySelector(".preview-box");
    if(pvBtn){
      pvBtn.addEventListener("click",async e=>{
        e.preventDefault();
        const showing=box.classList.contains("on");
        if(showing){box.classList.remove("on");ta.style.display="";pvBtn.textContent="Preview";return;}
        const fd=new FormData();fd.append("md",ta.value);
        fd.append("csrfmiddlewaretoken",document.querySelector("[name=csrfmiddlewaretoken]").value);
        const r=await fetch(PREVIEW_URL,{method:"POST",body:fd,headers:{"X-Requested-With":"fetch"}});
        const j=await r.json();
        box.innerHTML='<div class="rendered">'+j.html+'</div>';
        box.classList.add("on");ta.style.display="none";pvBtn.textContent="Edit";
      });
    }
  });
  // Editor sub-tab switching (Knowledge / Testing)
  document.querySelectorAll(".edit-tab").forEach(tab=>{
    tab.addEventListener("click",e=>{
      e.preventDefault();
      const key=tab.dataset.for;
      document.querySelectorAll(".edit-tab").forEach(t=>t.classList.toggle("on",t===tab));
      document.querySelectorAll(".editor-pane").forEach(p=>p.classList.toggle("on",p.dataset.pane===key));
    });
  });
  // Further Reading rows
  const list=document.querySelector(".links-editor");
  if(list){
    const add=document.querySelector(".addrow");
    add&&add.addEventListener("click",e=>{
      e.preventDefault();
      const row=document.createElement("div");row.className="link-row";
      row.innerHTML='<input class="in" name="link_label" placeholder="Label">'+
        '<input class="in" name="link_url" type="url" placeholder="https://">'+
        '<button class="rm" title="Remove">&times;</button>';
      list.insertBefore(row,add);
    });
    list.addEventListener("click",e=>{
      if(e.target.classList.contains("rm")){e.preventDefault();e.target.closest(".link-row").remove();}
    });
  }
})();
