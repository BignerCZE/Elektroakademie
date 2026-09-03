(function () {
    "use strict";

    const CURRENT_KEY = "elektroakademie_order_draft_v2";
    const SUPPORTED_KEYS = Object.freeze([
        "elektroakademie_order_draft",
        CURRENT_KEY,
        "elektroakademie_order_draft_v3"
    ]);

    window.ElektroakademieOrderDraft = Object.freeze({
        currentKey: CURRENT_KEY,
        supportedKeys: SUPPORTED_KEYS,
        exists: function () {
            return SUPPORTED_KEYS.some(function (key) {
                return localStorage.getItem(key) !== null;
            });
        },
        clear: function () {
            SUPPORTED_KEYS.forEach(function (key) {
                localStorage.removeItem(key);
            });
        }
    });
}());
