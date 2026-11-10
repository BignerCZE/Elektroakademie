// A restored activation form must revalidate its single-use token on the server.
window.addEventListener("pageshow", (event) => {
    const navigation = performance.getEntriesByType("navigation")[0];
    if (event.persisted || navigation?.type === "back_forward") {
        window.location.replace(window.location.href);
    }
});
