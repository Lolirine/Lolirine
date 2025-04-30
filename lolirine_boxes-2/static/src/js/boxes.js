odoo.define('lolirine_boxes.init', function (require) {
  document.addEventListener('DOMContentLoaded', () => {
    const url = "/web/static/boxes.json";
    fetch(url).then(r => r.json()).then(data => {
      const rdc = data.filter(b => b.code.startsWith("1"));
      const etage = data.filter(b => b.code.startsWith("2"));
      const container = document.getElementById("boxes-view");
      const section = (label, items) => {
        const zone = items.map(box => `<div class='box ${box.etat}' onclick='openModal(${JSON.stringify(box)})'>${box.code}</div>`).join("");
        return `<h3>${label}</h3><div class='zone'>${zone}</div>`;
      };
      container.innerHTML = section("Rez-de-chaussée", rdc) + section("1er étage", etage);
    });
  });
});
