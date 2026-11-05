'use strict';
const $ = id => document.getElementById(id);
const money = n => new Intl.NumberFormat('es-MX', {style:'currency', currency:'MXN'}).format(Number(n));
let catalogo = [];
let seleccionado = null;
let requestNumber = 0;
const errorMessage = (element, msg, ok=false) => { element.textContent=msg; element.className='message '+(ok?'ok':'bad'); };
async function apiFetch(url, options={}) {
  const response=await fetch(url, options);
  const content=await response.json().catch(()=>({error:'No se pudo leer la respuesta del servidor.'}));
  if(!response.ok) throw new Error(content.error || 'Ocurrió un error.');
  return content;
}
function createCell(tr, text, className='') {
  const td=document.createElement('td'); td.textContent=text; if(className)td.className=className; tr.append(td); return td;
}
function renderTable(items) {
  const table=$('tablaProductos'); table.replaceChildren();
  $('contador').textContent=`${items.length} producto${items.length===1?'':'s'}`;
  if(!items.length){const tr=document.createElement('tr');const td=createCell(tr,'No se encontraron productos.','empty');td.colSpan=6;table.append(tr);return;}
  for(const p of items){
    const tr=document.createElement('tr');
    const productTd=document.createElement('td');productTd.className='product-info';
    const name=document.createElement('strong');name.textContent=p.nombre;
    const desc=document.createElement('small');desc.textContent=p.descripcion || 'Sin descripción';
    productTd.append(name,desc);tr.append(productTd);
    createCell(tr,p.marca||'—');createCell(tr,money(p.precio),'price');
    const stock=createCell(tr,p.stock);stock.className=p.stock===0?'stock out':'stock';
    const imageTd=document.createElement('td');
    if(p.imagen){const img=document.createElement('img');img.className='product-image';img.src=p.imagen;img.alt=`Imagen de ${p.nombre}`;imageTd.append(img);} else {const ph=document.createElement('span');ph.className='no-image';ph.textContent='▧';imageTd.append(ph);}
    tr.append(imageTd);
    const action=document.createElement('td');const button=document.createElement('button');button.textContent=p.stock===0?'Agotado':'Vender';button.className='btn mini';button.disabled=p.stock===0;button.addEventListener('click',()=>openSale(p));action.append(button);tr.append(action);
    table.append(tr);
  }
}
async function loadProducts() {
  const current=++requestNumber;
  const query=$('busqueda').value.trim();
  try {
    const data=await apiFetch(`/api/productos?q=${encodeURIComponent(query)}`);
    if(current!==requestNumber)return;
    renderTable(data.productos);
    const all=query?await apiFetch('/api/productos'):data;
    catalogo=all.productos;
    $('totalProductos').textContent=catalogo.length;
    $('totalUnidades').textContent=catalogo.reduce((n,p)=>n+p.stock,0);
    $('sinStock').textContent=catalogo.filter(p=>p.stock===0).length;
  } catch(err){errorMessage($('formMessage'),err.message);}
}
$('formProducto').addEventListener('submit',async event=>{
  event.preventDefault();const button=$('btnGuardar');button.disabled=true;errorMessage($('formMessage'),'');
  try{
    const formData=new FormData(event.currentTarget);
    const result=await apiFetch('/api/productos',{method:'POST',headers:{'X-CSRF-Token':window.CSRF_TOKEN},body:formData});
    event.currentTarget.reset();$('preview').hidden=true;$('preview').removeAttribute('src');$('uploadPlaceholder').hidden=false;
    $('busqueda').value='';await loadProducts();errorMessage($('formMessage'),result.mensaje,true);
  }catch(err){errorMessage($('formMessage'),err.message);}finally{button.disabled=false;}
});
$('imagen').addEventListener('change',event=>{
  const file=event.target.files[0];if(!file){$('preview').hidden=true;$('uploadPlaceholder').hidden=false;return;}
  if(file.size>5*1024*1024){errorMessage($('formMessage'),'La imagen supera los 5 MB.');event.target.value='';return;}
  const reader=new FileReader();reader.onload=()=>{$('preview').src=reader.result;$('preview').hidden=false;$('uploadPlaceholder').hidden=true;};reader.readAsDataURL(file);
});
let searchTimer;
$('busqueda').addEventListener('input',()=>{clearTimeout(searchTimer);searchTimer=setTimeout(loadProducts,180);});
$('btnActualizar').addEventListener('click',loadProducts);
function openSale(product){seleccionado=product;$('ventaNombre').textContent=product.nombre;$('ventaPrecio').textContent=money(product.precio);$('ventaStock').textContent=product.stock;$('ventaCantidad').value=1;$('ventaCantidad').max=product.stock;errorMessage($('ventaMensaje'),'');updateTotal();$('modalVenta').hidden=false;$('ventaCantidad').focus();}
function closeSale(){$('modalVenta').hidden=true;seleccionado=null;}
function updateTotal(){if(!seleccionado)return;const qty=Number($('ventaCantidad').value);$('ventaTotal').textContent=money(qty>0?qty*Number(seleccionado.precio):0);}
$('ventaCantidad').addEventListener('input',updateTotal);
$('cerrarModal').addEventListener('click',closeSale);$('cancelarVenta').addEventListener('click',closeSale);
$('modalVenta').addEventListener('click',e=>{if(e.target===$('modalVenta'))closeSale();});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!$('modalVenta').hidden)closeSale();});
$('confirmarVenta').addEventListener('click',async()=>{
  if(!seleccionado)return;
  const cantidad=Number($('ventaCantidad').value);
  if(!Number.isInteger(cantidad)||cantidad<1||cantidad>seleccionado.stock){errorMessage($('ventaMensaje'),'Ingresa una cantidad válida dentro del stock disponible.');return;}
  const button=$('confirmarVenta');button.disabled=true;
  try{
    const result=await apiFetch('/api/vender',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':window.CSRF_TOKEN},body:JSON.stringify({producto_id:seleccionado.id,cantidad})});
    closeSale();await loadProducts();errorMessage($('formMessage'),`Venta #${result.venta_id} confirmada por ${money(result.total)}.`,true);
  }catch(err){errorMessage($('ventaMensaje'),err.message);}finally{button.disabled=false;}
});
loadProducts();
