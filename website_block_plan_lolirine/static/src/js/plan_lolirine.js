document.addEventListener("DOMContentLoaded", function () {
  const buttons = document.querySelectorAll(".legend-buttons button");
  const svg = document.querySelector(".svg-container svg");

  buttons.forEach(button => {
    button.addEventListener("click", () => {
      const filter = button.dataset.filter;
      const allElements = svg.querySelectorAll("[data-status]");

      allElements.forEach(el => {
        const status = el.getAttribute("data-status");
        if (status === filter) {
          el.style.opacity = "1";
        } else {
          el.style.opacity = "0.2";
        }
      });
    });
  });
});
