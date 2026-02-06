document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-href].pv-clickable-row").forEach((row) => {
        row.addEventListener("click", (event) => {
            if (event.target.closest("a, button, input, label, select, textarea")) {
                return;
            }
            const href = row.getAttribute("data-href");
            if (href) {
                window.location.href = href;
            }
        });
    });
});
