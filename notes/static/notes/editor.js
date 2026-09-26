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
  // Prefix EVERY line spanned by the selection. makePrefix(i) builds the
  // prefix for the i-th selected line (so numbered lists count up).
  function prefixLines(ta, makePrefix){
    const s=ta.selectionStart, e=ta.selectionEnd, v=ta.value;
    const blockStart=v.lastIndexOf("\n",s-1)+1;
    let blockEnd=v.indexOf("\n",e);
    if(blockEnd===-1)blockEnd=v.length;
    const block=v.slice(blockStart,blockEnd);
    const lines=block.split("\n");
    const out=lines.map((ln,i)=>makePrefix(i)+ln).join("\n");
    ta.value=v.slice(0,blockStart)+out+v.slice(blockEnd);
    ta.focus();
    ta.selectionStart=blockStart;
    ta.selectionEnd=blockStart+out.length;
  }
  const actions={
    bold:t=>surround(t,"**","**","bold text"),
    italic:t=>surround(t,"*","*","italic text"),
    code:t=>surround(t,"`","`","code"),
    codeblock:t=>surround(t,"\n```bash\n","\n```\n","command here"),
    h2:t=>linePrefix(t,"## "),
    h3:t=>linePrefix(t,"### "),
    ul:t=>prefixLines(t,()=>"- "),
    ol:t=>prefixLines(t,i=>`${i+1}. `),
    quote:t=>prefixLines(t,()=>"> "),
    link:t=>surround(t,"[","](https://)","label"),
    table:t=>surround(t,"\n| Col A | Col B |\n|---|---|\n| a | b |\n","","")
  };
  document.querySelectorAll(".toolbar").forEach(bar=>{
    const pane=bar.closest(".editor-pane");
    const ta=pane.querySelector(".md-area");
    bar.querySelectorAll(".tb[data-act]").forEach(btn=>{
      btn.addEventListener("click",e=>{e.preventDefault();actions[btn.dataset.act](ta);});
    });

    // Color popover
    const colorBtn=bar.querySelector("[data-color-btn]");
    const pop=bar.querySelector(".color-pop");
    if(colorBtn&&pop){
      colorBtn.addEventListener("click",e=>{e.preventDefault();e.stopPropagation();
        document.querySelectorAll(".color-pop.on").forEach(p=>{if(p!==pop)p.classList.remove("on");});
        pop.classList.toggle("on");});
      pop.querySelectorAll(".swatch").forEach(sw=>{
        sw.addEventListener("click",e=>{
          e.preventDefault();
          const hex=sw.dataset.color.toLowerCase();
          const s=ta.selectionStart,en=ta.selectionEnd,v=ta.value;
          const sel=v.slice(s,en)||"text";
          const wrapped='<span class="clr-'+hex+'">'+sel+'</span>';
          ta.value=v.slice(0,s)+wrapped+v.slice(en);
          ta.focus();
          const caret=s+('<span class="clr-'+hex+'">').length;
          ta.selectionStart=caret; ta.selectionEnd=caret+sel.length;
          pop.classList.remove("on");
        });
      });
    }
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
  // Tag picker search filter
  (function(){
    const search=document.querySelector(".tag-search");
    if(!search)return;
    const opts=[...document.querySelectorAll(".tag-opt")];
    search.addEventListener("input",()=>{
      const q=search.value.trim().toLowerCase();
      opts.forEach(o=>o.classList.toggle("hidden", q && !o.dataset.name.includes(q)));
    });
  })();

  // Close color popovers on outside click
  document.addEventListener("click",()=>document.querySelectorAll(".color-pop.on").forEach(p=>p.classList.remove("on")));

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
