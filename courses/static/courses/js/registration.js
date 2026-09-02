document.addEventListener("DOMContentLoaded", function () {
    const ORDER_DRAFT_KEY = "elektroakademie_order_draft_v2";
    const ORDER_DRAFT_KEYS = [
        "elektroakademie_order_draft",
        "elektroakademie_order_draft_v2",
        "elektroakademie_order_draft_v3"
    ];
    const registrationForm = document.getElementById("registration-form");
    const hasParticipantServerErrors =
        registrationForm.dataset.participantServerErrors === "true";
    const hasBillingServerErrors =
        registrationForm.dataset.billingServerErrors === "true";

    const courses = {
        "4": {
            title: "Zkouška odborné způsobilosti §4 – osoba poučená",
            shortTitle: "§4 – osoba poučená",
            meta: "Online školení",
            price: 990,
            detailTitle: "Popis školení §4 – OSOBA POUČENÁ",
            detailHtml: `
                <p>Online školení a přezkoušení pro osoby bez elektrotechnického vzdělání určené k získání odborné způsobilosti „osoba poučená“ dle §4 NV 194/2022 Sb.</p>
                <p>Příprava probíhá kompletně online formou e-learningu v souladu se zákonem č. 250/2021 Sb. a NV 194/2022 Sb. Studijní materiály i závěrečné testy jsou dostupné přes počítač nebo mobilní zařízení z pohodlí domova.</p>
                <p>Velkou výhodou online formy je možnost studovat vlastním tempem. Přístup do e-learningového systému je aktivní po dobu 60 dnů.</p>
                <h3>Jaké činnosti může osoba poučená vykonávat?</h3>
                <ul>
                    <li>samostatná obsluha elektrických zařízení v rozsahu určeném pro obsluhu,</li>
                    <li>práce na elektrických zařízeních bez napětí a v jejich blízkosti podle pokynů,</li>
                    <li>práce pod dozorem osoby znalé podle stanovených pracovních postupů.</li>
                </ul>
                <h3>Jak školení probíhá?</h3>
                <ul>
                    <li>objednáte školení prostřednictvím objednávky na webu,</li>
                    <li>obdržíte zálohovou fakturu a přístupy do e-learningu,</li>
                    <li>absolvujete samostudium a online testy,</li>
                    <li>po splnění podmínek obdržíte Zápis o provedení poučení.</li>
                </ul>
                <h3>V ceně kurzu je zahrnuto</h3>
                <ul>
                    <li>organizační zajištění školení,</li>
                    <li>přístup do e-learningu na 60 dnů,</li>
                    <li>online studijní materiály a testy,</li>
                    <li>vystavení Zápisu o provedení poučení.</li>
                </ul>
            `
        },
        "6": {
            title: "Zkouška odborné způsobilosti §6 – elektrotechnik",
            shortTitle: "§6 – elektrotechnik",
            meta: "Kombinované školení",
            price: 2990,
            detailTitle: "Popis školení §6 – Elektrotechnik",
            detailHtml: `
                <p>Online příprava ke zkoušce odborné způsobilosti dle §6 NV 194/2022 Sb. je určena pro osoby s elektrotechnickým vzděláním, které vykonávají samostatnou práci na elektrických zařízeních.</p>
                <p>Školení probíhá kombinovanou formou. Studijní materiály a testy jsou dostupné online prostřednictvím e-learningu. Ústní část zkoušky probíhá prezenčně.</p>
                <h3>Co opravňuje §6 – Elektrotechnik</h3>
                <p>Osoba znalá podle §6 může samostatně vykonávat činnosti na elektrických zařízeních a pracovat v jejich blízkosti bez neustálého dohledu.</p>
                <h3>Možná rozšíření zkoušky</h3>
                <ul>
                    <li>hromosvody (LPS),</li>
                    <li>bez omezení napětí,</li>
                    <li>prostory s nebezpečím výbuchu (Ex).</li>
                </ul>
                <h3>Kdo nejčastěji potřebuje §6</h3>
                <ul>
                    <li>elektrotechnici ve výrobě a průmyslu,</li>
                    <li>pracovníci montáže a elektro údržby,</li>
                    <li>servisní technici,</li>
                    <li>budoucí revizní technici elektro.</li>
                </ul>
                <h3>V ceně kurzu</h3>
                <ul>
                    <li>přístup do e-learningu na 60 dnů,</li>
                    <li>online studijní materiály a testy,</li>
                    <li>odborná příprava k přezkoušení,</li>
                    <li>prezenční ústní zkouška,</li>
                    <li>vystavení Dokladu o složení zkoušky.</li>
                </ul>
            `
        },
        "7": {
            title: "Zkouška odborné způsobilosti §7 – vedoucí elektrotechnik",
            shortTitle: "§7 – vedoucí elektrotechnik",
            meta: "Kombinované školení",
            price: 3490,
            detailTitle: "Popis školení §7 – Vedoucí elektrotechnik",
            detailHtml: `
                <p>Online příprava ke zkoušce odborné způsobilosti dle §7 NV 194/2022 Sb. je určena pro osoby s elektrotechnickým vzděláním, které vykonávají nebo budou vykonávat řídicí, kontrolní a organizační činnosti v elektrotechnice.</p>
                <p>Školení probíhá kombinovanou formou. Studijní materiály a testy jsou dostupné online prostřednictvím e-learningu. Ústní část zkoušky probíhá prezenčně.</p>
                <h3>Co opravňuje §7 – Vedoucí elektrotechnik</h3>
                <p>Osoba znalá podle §7 může vykonávat všechny činnosti elektrotechnika dle §6 a zároveň řídit činnosti na elektrických zařízeních a vykonávat odborný dohled.</p>
                <h3>Kdo nejčastěji potřebuje §7</h3>
                <ul>
                    <li>vedoucí pracovníci elektro provozů,</li>
                    <li>osoby řídící montáže a elektro údržbu,</li>
                    <li>projektanti elektrických zařízení,</li>
                    <li>budoucí revizní technici elektro.</li>
                </ul>
                <h3>Možná rozšíření zkoušky</h3>
                <ul>
                    <li>hromosvody (LPS),</li>
                    <li>bez omezení napětí,</li>
                    <li>prostory s nebezpečím výbuchu (Ex).</li>
                </ul>
                <h3>V ceně kurzu</h3>
                <ul>
                    <li>přístup do e-learningu na 60 dnů,</li>
                    <li>online studijní materiály a testy,</li>
                    <li>odborná příprava k přezkoušení,</li>
                    <li>prezenční ústní zkouška,</li>
                    <li>vystavení Dokladu o složení zkoušky.</li>
                </ul>
            `
        }
    };

    const selectedCourseInput = document.getElementById("selected-course-input");
    const addButton = document.getElementById("add-participant-button");
    const wrapper = document.getElementById("participants-wrapper");
    const totalFormsInput = document.getElementById("id_participants-TOTAL_FORMS");
    const goToFinalSummaryButton = document.getElementById("go-to-final-summary-button");
    const summaryPreviousButton = document.getElementById("summary-previous-button");
    const checkoutBackButton = document.getElementById("checkout-back-button");
    const goToParticipantsButton = document.getElementById("go-to-participants-button");
    const participantsToBillingButton = document.getElementById("participants-to-billing-button");
    const participantsErrorMessage = document.getElementById("participants-error-message");
    const billingErrorMessage = document.getElementById("billing-error-message");
    const termsAgreement = document.getElementById("terms-agreement");
    const termsAgreementLabel = document.querySelector(".terms-agreement-label");

    const icoInput = document.querySelector('[name="ico"]');
    const dicInput = document.querySelector('[name="dic"]');
    const companyNameInput = document.querySelector('[name="company_name"]');
    const streetInput = document.querySelector('[name="street"]');
    const cityInput = document.querySelector('[name="city"]');
    const zipCodeInput = document.querySelector('[name="zip_code"]');
    const countryInput = document.querySelector('[name="country"]');
    const loadAresButton = document.getElementById("load-ares-button");
    const aresStatus = document.getElementById("ares-status");

    let aresRequestController = null;

    function setAresStatus(message, state = "") {
        if (!aresStatus) {
            return;
        }

        aresStatus.textContent = message;
        aresStatus.classList.remove("is-loading", "is-success", "is-error");

        if (state) {
            aresStatus.classList.add("is-" + state);
        }
    }

    function normalizeIco(value) {
        return String(value || "").replace(/\D/g, "").slice(0, 8);
    }

    function dispatchFieldUpdate(input) {
        if (!input) {
            return;
        }

        input.dispatchEvent(new Event("input", { bubbles: true }));
        input.dispatchEvent(new Event("change", { bubbles: true }));
    }

    function setCountryFromAres(countryName) {
        if (!countryInput) {
            return;
        }

        const value = countryName || "Česká republika";

        if (countryInput.tagName === "SELECT") {
            const normalizedCountry = value.trim().toLocaleLowerCase("cs-CZ");

            const matchingOption = Array.from(countryInput.options).find(function (option) {
                const optionText = option.textContent.trim().toLocaleLowerCase("cs-CZ");
                const optionValue = option.value.trim().toLocaleLowerCase("cs-CZ");

                return optionText === normalizedCountry || optionValue === normalizedCountry;
            });

            if (matchingOption) {
                countryInput.value = matchingOption.value;
                dispatchFieldUpdate(countryInput);
            }

            return;
        }

        countryInput.value = value;
        dispatchFieldUpdate(countryInput);
    }

    function fillBillingFromAres(company) {
        const fieldValues = [
            [dicInput, company.dic || ""],
            [companyNameInput, company.name || ""],
            [streetInput, company.street || ""],
            [cityInput, company.city || ""],
            [zipCodeInput, company.postal_code || ""]
        ];

        fieldValues.forEach(function ([input, value]) {
            if (!input) {
                return;
            }

            input.value = value;
            input.classList.remove("field-error");
            dispatchFieldUpdate(input);
        });

        setCountryFromAres(company.country || "Česká republika");
        clearValidationMessage(billingErrorMessage);
        saveOrderDraft();
    }

    async function loadCompanyFromAres() {
        if (!icoInput || !loadAresButton) {
            return;
        }

        const ico = normalizeIco(icoInput.value);
        icoInput.value = ico;
        icoInput.classList.remove("field-error");

        if (ico.length !== 8) {
            icoInput.classList.add("field-error");
            setAresStatus("IČO musí obsahovat přesně 8 číslic.", "error");
            icoInput.focus();
            return;
        }

        if (aresRequestController) {
            aresRequestController.abort();
        }

        aresRequestController = new AbortController();

        const originalButtonText = loadAresButton.textContent;
        loadAresButton.disabled = true;
        loadAresButton.textContent = "Načítám…";

        icoInput.classList.add("ares-loading");
        icoInput.setAttribute("aria-busy", "true");
        setAresStatus("Načítám údaje z ARES…", "loading");

        try {
            const response = await fetch(`/api/ares/${encodeURIComponent(ico)}/`, {
                method: "GET",
                headers: {
                    "Accept": "application/json",
                    "X-Requested-With": "XMLHttpRequest"
                },
                signal: aresRequestController.signal
            });

            let data;

            try {
                data = await response.json();
            } catch (error) {
                throw new Error("Server nevrátil platnou odpověď.");
            }

            if (!response.ok || !data.success || !data.company) {
                throw new Error(
                    data.message || "Subjekt se nepodařilo v ARES načíst."
                );
            }

            fillBillingFromAres(data.company);
            setAresStatus("Fakturační údaje byly doplněny z ARES.", "success");
        } catch (error) {
            if (error.name === "AbortError") {
                return;
            }

            console.error("Chyba při načítání ARES:", error);

            setAresStatus(
                error.message || "ARES je momentálně nedostupný. Údaje vyplňte ručně.",
                "error"
            );
        } finally {
            icoInput.classList.remove("ares-loading");
            icoInput.removeAttribute("aria-busy");
            loadAresButton.disabled = false;
            loadAresButton.textContent = originalButtonText;
            aresRequestController = null;
        }
    }

    if (icoInput) {
        icoInput.setAttribute("inputmode", "numeric");
        icoInput.setAttribute("autocomplete", "organization");
        icoInput.setAttribute("maxlength", "8");

        icoInput.addEventListener("input", function () {
            const normalizedValue = normalizeIco(icoInput.value);

            if (icoInput.value !== normalizedValue) {
                icoInput.value = normalizedValue;
            }

            icoInput.classList.remove("field-error");
            setAresStatus("");
        });

        icoInput.addEventListener("keydown", function (event) {
            if (event.key === "Enter") {
                event.preventDefault();
                loadCompanyFromAres();
            }
        });
    }

    if (loadAresButton) {
        loadAresButton.addEventListener("click", loadCompanyFromAres);
    }

    function openLegalModal(modalId) {
        const modal = document.getElementById(modalId);

        if (!modal) {
            return;
        }

        modal.classList.add("is-open");
        modal.setAttribute("aria-hidden", "false");
        document.body.classList.add("legal-modal-open");

        const closeButton = modal.querySelector("[data-legal-modal-close]");

        if (closeButton) {
            closeButton.focus();
        }
    }

    function closeLegalModal(modal) {
        if (!modal) {
            return;
        }

        modal.classList.remove("is-open");
        modal.setAttribute("aria-hidden", "true");
        document.body.classList.remove("legal-modal-open");
    }

    document.querySelectorAll("[data-legal-modal-open]").forEach(function (link) {
        link.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();

            openLegalModal(link.dataset.legalModalOpen);
        });
    });

    document.querySelectorAll(".legal-modal-overlay").forEach(function (modal) {
        modal.addEventListener("click", function (event) {
            if (event.target === modal) {
                closeLegalModal(modal);
            }
        });

        modal.querySelectorAll("[data-legal-modal-close]").forEach(function (button) {
            button.addEventListener("click", function () {
                closeLegalModal(modal);
            });
        });
    });

    document.addEventListener("keydown", function (event) {
        if (event.key !== "Escape") {
            return;
        }

        document.querySelectorAll(".legal-modal-overlay.is-open").forEach(function (modal) {
            closeLegalModal(modal);
        });
    });


    const stepButtons = document.querySelectorAll("[data-step-button]");
    const stepPanels = document.querySelectorAll("[data-step-panel]");
    const courseButtons = document.querySelectorAll("[data-course-select]");

    const courseInfoActionCard = document.getElementById("course-info-action-card");
    const orderSummaryCard = document.getElementById("order-summary-card");
    const finalSummaryConsent = document.getElementById("final-summary-consent");
    const finalSummaryConsentInput = finalSummaryConsent ? finalSummaryConsent.querySelector("input") : null;

    const selectedCourseTitle = document.getElementById("selected-course-title");
    const selectedCourseContent = document.getElementById("selected-course-content");
    const registerProductTitle = document.getElementById("register-product-title");
    const registerProductMeta = document.getElementById("register-product-meta");
    const registerProductPrice = document.getElementById("register-product-price");
    const summaryCount = document.getElementById("summary-count");
    const summaryProductTitle = document.getElementById("summary-product-title");
    const summaryProductMeta = document.getElementById("summary-product-meta");
    const summaryProductPrice = document.getElementById("summary-product-price");
    const summaryTotalVat = document.getElementById("summary-total-vat");
    const summaryTotalNoVat = document.getElementById("summary-total-no-vat");


    function formatPrice(value) {
        return value.toLocaleString("cs-CZ") + " Kč";
    }

    function getActiveCourse() {
        return courses[selectedCourseInput.value];
    }

    function getParticipantCount() {
        return wrapper.querySelectorAll(".participant-item").length;
    }

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function getInputValue(name) {
        const input = document.querySelector(`[name="${name}"]`);
        return input ? input.value.trim() : "";
    }

    function getOrderDraft() {
        try {
            const rawDraft = localStorage.getItem(ORDER_DRAFT_KEY);

            if (!rawDraft) {
                return null;
            }

            const draft = JSON.parse(rawDraft);

            if (
                !draft
                || !draft.selected_course
                || !Array.isArray(draft.participants)
                || draft.participants.length < 1
            ) {
                localStorage.removeItem(ORDER_DRAFT_KEY);
                return null;
            }

            return draft;
        } catch (error) {
            localStorage.removeItem(ORDER_DRAFT_KEY);
            return null;
        }
    }

    function saveOrderDraft() {
        const courseId = selectedCourseInput.value;

        if (!courseId) {
            return;
        }

        const participants = Array.from(wrapper.querySelectorAll(".participant-item")).map(function (participant) {
            return {
                first_name: participant.querySelector("input[name$='first_name']")?.value || "",
                last_name: participant.querySelector("input[name$='last_name']")?.value || "",
                email: participant.querySelector("input[name$='email']")?.value || ""
            };
        });

        const billing = {};

        document.querySelectorAll(".billing-grid input, .billing-grid textarea, .billing-grid select").forEach(function (input) {
            if (!input.name) {
                return;
            }

            billing[input.name] = input.type === "checkbox" ? input.checked : input.value;
        });
        const activePanel = document.querySelector(".checkout-step-panel:not([hidden])");
        const currentStep = activePanel ? Number(activePanel.dataset.stepPanel) : 3;

        localStorage.setItem(
            ORDER_DRAFT_KEY,
            JSON.stringify({
                selected_course: courseId,
                participants: participants,
                billing: billing,
                current_step: currentStep,
                saved_at: new Date().toISOString()
            })
        );
    }

    function cloneParticipant() {
        const formCount = Number(totalFormsInput.value);
        const firstParticipant = wrapper.querySelector(".participant-item");
        const newParticipant = firstParticipant.cloneNode(true);

        newParticipant.querySelectorAll("input").forEach(function (input) {
            input.name = input.name.replace(/participants-\d+-/, "participants-" + formCount + "-");
            input.id = input.id.replace(/participants-\d+-/, "participants-" + formCount + "-");
            input.classList.remove("field-error");
            input.value = "";
        });

        newParticipant.querySelectorAll(".errorlist").forEach(function (errorList) {
            errorList.remove();
        });

        newParticipant.classList.remove("participant-card--error");

        newParticipant
            .querySelectorAll("[data-participant-email-error]")
            .forEach(function (errorElement) {
                errorElement.textContent = "";
                errorElement.hidden = true;
            });

        wrapper.appendChild(newParticipant);
        totalFormsInput.value = formCount + 1;

        return newParticipant;
    }

    function ensureParticipantCount(count) {
        while (wrapper.querySelectorAll(".participant-item").length < count) {
            cloneParticipant();
        }
    }

    function restoreOrderDraft() {
        const draft = getOrderDraft();

        if (!draft || !draft.selected_course || !courses[draft.selected_course]) {
            showStep(1);
            return;
        }

        updateCourseView(draft.selected_course);

        if (Array.isArray(draft.participants) && draft.participants.length) {
            const nonEmptyParticipants = draft.participants.filter(function (participant) {
                return Boolean(
                    (participant.first_name || "").trim()
                    || (participant.last_name || "").trim()
                    || (participant.email || "").trim()
                );
            });

            const participantsToRestore = nonEmptyParticipants.length
                ? draft.participants
                : [draft.participants[0]];

            ensureParticipantCount(participantsToRestore.length);

            while (
                wrapper.querySelectorAll(".participant-item").length
                > participantsToRestore.length
            ) {
                wrapper.lastElementChild.remove();
            }

            wrapper.querySelectorAll(".participant-item").forEach(function (participant, index) {
                const participantData = participantsToRestore[index] || {};

                const firstNameInput = participant.querySelector("input[name$='first_name']");
                const lastNameInput = participant.querySelector("input[name$='last_name']");
                const emailInput = participant.querySelector("input[name$='email']");

                if (firstNameInput) {
                    firstNameInput.value = participantData.first_name || "";
                }

                if (lastNameInput) {
                    lastNameInput.value = participantData.last_name || "";
                }

                if (emailInput) {
                    emailInput.value = participantData.email || "";
                }
            });
        }

        if (draft.billing) {
            Object.keys(draft.billing).forEach(function (name) {
                const input = document.querySelector(`[name="${name}"]`);

                if (!input) {
                    return;
                }

                if (input.type === "checkbox") {
                    input.checked = Boolean(draft.billing[name]);
                } else {
                    input.value = draft.billing[name] || "";
                }
            });
        }

        refreshParticipants();
        updateOrderSummary();

        const restoredStep = Number(draft.current_step) || 3;

        if (restoredStep >= 1 && restoredStep <= 5) {
            showStep(restoredStep);
        } else {
            showStep(3);
        }
    }

    function showValidationMessage(container, title, messages) {
        if (!container) {
            return;
        }

        container.innerHTML = `
            <strong>${escapeHtml(title)}</strong>
            <ul>
                ${messages.map(function (message) {
            return `<li>${escapeHtml(message)}</li>`;
        }).join("")}
            </ul>
        `;
        container.hidden = false;
    }

    function clearValidationMessage(container) {
        if (!container) {
            return;
        }

        container.hidden = true;
        container.innerHTML = "";
    }

    function clearParticipantEmailErrors() {
        wrapper.querySelectorAll("[data-participant-email-error]").forEach(function (errorElement) {
            errorElement.textContent = "";
            errorElement.hidden = true;
        });

        wrapper.querySelectorAll('input[name$="-email"]').forEach(function (emailInput) {
            emailInput.classList.remove("field-error");
            emailInput.removeAttribute("aria-invalid");
        });

        wrapper.querySelectorAll(".participant-card--error").forEach(function (participantCard) {
            participantCard.classList.remove("participant-card--error");
        });
    }

    function showParticipantEmailError(emailInput, message) {
        emailInput.classList.add("field-error");
        emailInput.setAttribute("aria-invalid", "true");

        const participantCard = emailInput.closest(".participant-card");

        if (participantCard) {
            participantCard.classList.add("participant-card--error");
        }

        const participantItem = emailInput.closest(".participant-item");

        if (!participantItem) {
            return;
        }

        const errorElement = participantItem.querySelector(
            "[data-participant-email-error]"
        );

        if (errorElement) {
            errorElement.textContent = message;
            errorElement.hidden = false;
        }
    }

    async function checkParticipantEmails() {
        clearParticipantEmailErrors();
        clearValidationMessage(participantsErrorMessage);

        const emailInputs = Array.from(
            wrapper.querySelectorAll('input[name$="-email"]')
        );

        const emails = emailInputs.map(function (emailInput) {
            return emailInput.value.trim().toLowerCase();
        });

        const csrfInput = document.querySelector(
            '#registration-form input[name="csrfmiddlewaretoken"]'
        );

        try {
            const response = await fetch(
                registrationForm.dataset.checkEmailsUrl,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfInput ? csrfInput.value : "",
                        "X-Requested-With": "XMLHttpRequest"
                    },
                    body: JSON.stringify({ emails: emails })
                }
            );

            let result;

            try {
                result = await response.json();
            } catch (error) {
                throw new Error("Server nevrátil platnou odpověď.");
            }

            if (!response.ok || !result.success) {
                throw new Error(
                    result.message || "Kontrolu e-mailů se nepodařilo provést."
                );
            }

            const occupiedEmails = new Set(result.occupied_emails || []);
            const duplicateEmails = new Set(result.duplicate_emails || []);
            let firstInvalidInput = null;
            let hasError = false;

            emailInputs.forEach(function (emailInput) {
                const normalizedEmail = emailInput.value.trim().toLowerCase();

                if (occupiedEmails.has(normalizedEmail)) {
                    showParticipantEmailError(
                        emailInput,
                        "Účet s touto e-mailovou adresou již existuje. Zadejte jinou adresu."
                    );
                    hasError = true;
                    firstInvalidInput = firstInvalidInput || emailInput;
                    return;
                }

                if (duplicateEmails.has(normalizedEmail)) {
                    showParticipantEmailError(
                        emailInput,
                        "Tato e-mailová adresa je v objednávce uvedena vícekrát."
                    );
                    hasError = true;
                    firstInvalidInput = firstInvalidInput || emailInput;
                }
            });

            if (hasError) {
                showValidationMessage(
                    participantsErrorMessage,
                    "Nelze pokračovat k fakturačním údajům.",
                    ["Opravte označené e-mailové adresy účastníků."]
                );

                if (firstInvalidInput) {
                    firstInvalidInput.scrollIntoView({
                        behavior: "smooth",
                        block: "center"
                    });
                    firstInvalidInput.focus();
                }

                return false;
            }

            return true;
        } catch (error) {
            console.error("Chyba při kontrole e-mailů:", error);

            showValidationMessage(
                participantsErrorMessage,
                "Kontrolu e-mailů nelze dokončit.",
                [
                    error.message ||
                    "Zkuste akci opakovat. Bez ověření e-mailů nelze pokračovat."
                ]
            );

            return false;
        }
    }

    function validateParticipants() {
        const participants = wrapper.querySelectorAll(".participant-item");
        let isValid = true;
        let firstInvalidInput = null;
        const messages = [];

        clearValidationMessage(participantsErrorMessage);

        participants.forEach(function (participant, index) {
            const participantNumber = index + 1;
            const fields = [
                [participant.querySelector("input[name$='first_name']"), "jméno"],
                [participant.querySelector("input[name$='last_name']"), "příjmení"],
                [participant.querySelector("input[name$='email']"), "e-mail"]
            ];

            const filledFields = [];
            const missingFields = [];

            fields.forEach(function ([input, label]) {
                if (!input) {
                    return;
                }

                if (!input.value.trim()) {
                    input.classList.add("field-error");
                    missingFields.push(label);
                    isValid = false;

                    if (!firstInvalidInput) {
                        firstInvalidInput = input;
                    }
                } else {
                    input.classList.remove("field-error");
                    filledFields.push(label);
                }
            });

            if (missingFields.length) {
                messages.push(
                    `Účastník č. ${participantNumber}: vyplněno ${filledFields.length ? filledFields.join(", ") : "nic"}; chybí ${missingFields.join(", ")}.`
                );
            }
        });

        if (!isValid) {
            showValidationMessage(
                participantsErrorMessage,
                "Nelze pokračovat. Chybí údaje u účastníků.",
                messages
            );

            if (firstInvalidInput) {
                firstInvalidInput.scrollIntoView({ behavior: "smooth", block: "center" });
                firstInvalidInput.focus();
            }
        }

        return isValid;
    }

    function validateBilling() {
        let isValid = true;
        let firstInvalidInput = null;
        const messages = [];

        clearValidationMessage(billingErrorMessage);

        const requiredBillingFields = [
            ["company_name", "název firmy / jméno objednatele"],
            ["street", "ulice"],
            ["city", "město"],
            ["zip_code", "PSČ"],
            ["country", "země"],
            ["contact_first_name", "jméno kontaktní osoby"],
            ["contact_last_name", "příjmení kontaktní osoby"],
            ["contact_phone_prefix", "telefonní předvolba"],
            ["contact_phone", "telefonní číslo"],
            ["contact_email", "e-mail kontaktní osoby"]
        ];

        requiredBillingFields.forEach(function ([name, label]) {
            const input = document.querySelector(`[name="${name}"]`);

            if (!input) {
                return;
            }

            if (!input.value.trim()) {
                input.classList.add("field-error");
                messages.push(`Chybí ${label}.`);
                isValid = false;

                if (!firstInvalidInput) {
                    firstInvalidInput = input;
                }
            } else {
                input.classList.remove("field-error");
            }
        });

        const contactEmailInput = document.querySelector(
            '[name="contact_email"]'
        );

        if (
            contactEmailInput &&
            contactEmailInput.value.trim() &&
            !contactEmailInput.validity.valid
        ) {
            contactEmailInput.classList.add("field-error");
            messages.push("E-mail kontaktní osoby nemá platný formát.");
            isValid = false;

            if (!firstInvalidInput) {
                firstInvalidInput = contactEmailInput;
            }
        }

        if (!isValid) {
            showValidationMessage(
                billingErrorMessage,
                "Nelze pokračovat. Chybí fakturační údaje.",
                messages
            );

            if (firstInvalidInput) {
                firstInvalidInput.scrollIntoView({ behavior: "smooth", block: "center" });
                firstInvalidInput.focus();
            }
        }

        return isValid;
    }

    function renderFinalSummary() {
        const course = getActiveCourse();
        const participantCount = getParticipantCount();

        if (!course) {
            return;
        }

        const totalVat = course.price * participantCount;

        const finalCourseTitle = document.getElementById("final-course-title");
        const finalCourseMeta = document.getElementById("final-course-meta");
        const finalParticipantCount = document.getElementById("final-participant-count");
        const finalBillingSummary = document.getElementById("final-billing-summary");
        const finalParticipantsSummary = document.getElementById("final-participants-summary");
        const finalOrderTotal = document.getElementById("final-order-total");

        if (!finalCourseTitle || !finalCourseMeta || !finalParticipantCount || !finalBillingSummary || !finalParticipantsSummary || !finalOrderTotal) {
            return;
        }

        finalCourseTitle.textContent = course.title;
        finalCourseMeta.textContent = course.meta;
        finalParticipantCount.textContent = String(participantCount);
        finalOrderTotal.textContent = formatPrice(totalVat);

        const countrySelect = document.querySelector('[name="country"]');

        const countryDisplayValue = countrySelect
            ? countrySelect.options[countrySelect.selectedIndex]?.textContent.trim() || ""
            : "";

        const billingRows = [
            ["IČO", getInputValue("ico")],
            ["DIČ", getInputValue("dic")],
            ["Firma", getInputValue("company_name")],
            ["Ulice", getInputValue("street")],
            ["Město", getInputValue("city")],
            ["PSČ", getInputValue("zip_code")],
            ["Země", countryDisplayValue],
            ["Kontaktní osoba", [
                getInputValue("contact_first_name"),
                getInputValue("contact_last_name")
            ].filter(Boolean).join(" ")],
            ["Telefon", [
                getInputValue("contact_phone_prefix"),
                getInputValue("contact_phone")
            ].filter(Boolean).join(" ")],
            ["Kontaktní e-mail", getInputValue("contact_email")],
            ["Poznámka", getInputValue("note")]
        ];

        finalBillingSummary.innerHTML = billingRows
            .filter(function (row) {
                return row[1];
            })
            .map(function (row) {
                return `
                    <div>
                        <dt>${escapeHtml(row[0])}</dt>
                        <dd>${escapeHtml(row[1])}</dd>
                    </div>
                `;
            })
            .join("");

        finalParticipantsSummary.innerHTML = Array.from(wrapper.querySelectorAll(".participant-item"))
            .map(function (participant) {
                const firstName = participant.querySelector("input[name$='first_name']")?.value.trim() || "";
                const lastName = participant.querySelector("input[name$='last_name']")?.value.trim() || "";
                const email = participant.querySelector("input[name$='email']")?.value.trim() || "";

                return `
                    <tr>
                        <td>${escapeHtml(firstName)}</td>
                        <td>${escapeHtml(lastName)}</td>
                        <td>${escapeHtml(email)}</td>
                    </tr>
                `;
            })
            .join("");
    }

    function showStep(step) {
        stepPanels.forEach(function (panel) {
            panel.hidden = panel.dataset.stepPanel !== String(step);
        });

        stepButtons.forEach(function (button) {
            button.classList.toggle(
                "checkout-step--active",
                button.dataset.stepButton === String(step)
            );
        });

        document.body.dataset.checkoutStep = String(step);
        checkoutBackButton.hidden = step === 1;

        courseInfoActionCard.hidden = step !== 2;
        orderSummaryCard.hidden = !(step === 3 || step === 4);
        participantsToBillingButton.hidden = step !== 3;
        goToFinalSummaryButton.hidden = step !== 4;

        const deleteOrderButton = document.getElementById("delete-order-button");
        deleteOrderButton.hidden = !(step === 3 || step === 4);

        if (finalSummaryConsentInput) {
            finalSummaryConsentInput.disabled = step !== 5;
        }

        if (step === 5) {
            renderFinalSummary();
        }

        if (selectedCourseInput.value && step >= 2) {
            const draft = getOrderDraft();

            if (draft) {
                draft.current_step = step;
                localStorage.setItem(
                    ORDER_DRAFT_KEY,
                    JSON.stringify(draft)
                );
            }
        }

        updateOrderSummary();
    }

    function updateCourseView(courseId) {
        const course = courses[courseId];

        if (!course) {
            return;
        }

        selectedCourseInput.value = courseId;
        selectedCourseTitle.textContent = course.detailTitle;
        selectedCourseContent.innerHTML = course.detailHtml;

        courseButtons.forEach(function (button) {
            button.classList.toggle("is-selected", button.dataset.courseSelect === courseId);
        });

        updateOrderSummary();
    }

    function updateOrderSummary() {
        const course = getActiveCourse();

        if (!course) {
            return;
        }

        const participantCount = getParticipantCount();
        const totalVat = course.price * participantCount;
        const totalNoVat = Math.round(totalVat / 1.21);

        registerProductTitle.textContent = course.title;
        registerProductMeta.innerHTML = `<strong>${course.meta}</strong>`;
        registerProductPrice.textContent = `${participantCount}× ${formatPrice(course.price)}`;

        summaryCount.textContent = participantCount + "×";
        summaryProductTitle.textContent = course.shortTitle;
        summaryProductMeta.textContent = course.meta;
        summaryProductPrice.textContent = formatPrice(totalVat);
        summaryTotalVat.textContent = formatPrice(totalVat);
        summaryTotalNoVat.textContent = formatPrice(totalNoVat);
    }

    function refreshParticipants() {
        const participants = wrapper.querySelectorAll(".participant-item");

        participants.forEach(function (participant, index) {
            participant.querySelector("h2").textContent = "Účastník " + (index + 1);

            const removeButton = participant.querySelector(".remove-participant-button");
            removeButton.hidden = participants.length === 1;
        });

        totalFormsInput.value = participants.length;
        updateOrderSummary();
    }

    courseButtons.forEach(function (button) {
        button.addEventListener("click", function () {
            const courseId = button.dataset.courseSelect;

            updateCourseView(courseId);
            saveOrderDraft();
            showStep(2);
            window.scrollTo({ top: 0, behavior: "smooth" });
        });
    });

    if (goToParticipantsButton) {
        goToParticipantsButton.addEventListener("click", function () {
            saveOrderDraft();
            showStep(3);
            window.scrollTo({ top: 0, behavior: "smooth" });
        });
    }

    let participantEmailCheckInProgress = false;

    if (participantsToBillingButton) {
        participantsToBillingButton.addEventListener("click", async function () {
            if (participantEmailCheckInProgress) {
                return;
            }

            if (!validateParticipants()) {
                return;
            }

            participantEmailCheckInProgress = true;
            participantsToBillingButton.disabled = true;

            const originalButtonText = participantsToBillingButton.textContent;
            participantsToBillingButton.textContent = "Kontroluji e-maily…";

            try {
                const emailsAreAvailable = await checkParticipantEmails();

                if (!emailsAreAvailable) {
                    return;
                }

                saveOrderDraft();
                showStep(4);
                window.scrollTo({ top: 0, behavior: "smooth" });
            } finally {
                participantEmailCheckInProgress = false;
                participantsToBillingButton.disabled = false;
                participantsToBillingButton.textContent = originalButtonText;
            }
        });
    }

    if (goToFinalSummaryButton) {
        goToFinalSummaryButton.addEventListener("click", function () {
            if (!validateBilling()) {
                return;
            }

            saveOrderDraft();
            renderFinalSummary();
            showStep(5);
            window.scrollTo({ top: 0, behavior: "smooth" });
        });
    }

    if (summaryPreviousButton) {
        summaryPreviousButton.addEventListener("click", function () {
            saveOrderDraft();
            showStep(4);
            window.scrollTo({ top: 0, behavior: "smooth" });
        });
    }

    if (addButton) {
        addButton.addEventListener("click", function () {
            const newParticipant = cloneParticipant();

            refreshParticipants();
            saveOrderDraft();

            newParticipant.scrollIntoView({
                behavior: "smooth",
                block: "center"
            });
        });
    }

    stepButtons.forEach(function (button) {
        button.addEventListener("click", async function () {
            const step = Number(button.dataset.stepButton);

            if (step > 1 && !selectedCourseInput.value) {
                showStep(1);
                return;
            }

            if (step >= 4) {
                if (!validateParticipants()) {
                    showStep(3);
                    return;
                }

                const emailsAreAvailable = await checkParticipantEmails();

                if (!emailsAreAvailable) {
                    showStep(3);
                    return;
                }
            }

            if (step === 5 && !validateBilling()) {
                showStep(4);
                return;
            }

            saveOrderDraft();
            showStep(step);
            window.scrollTo({ top: 0, behavior: "smooth" });
        });
    });

    checkoutBackButton.addEventListener("click", function () {
        const activePanel = document.querySelector(".checkout-step-panel:not([hidden])");
        const activeStep = activePanel ? Number(activePanel.dataset.stepPanel) : 1;

        saveOrderDraft();
        showStep(Math.max(1, activeStep - 1));
        window.scrollTo({ top: 0, behavior: "smooth" });
    });

    wrapper.addEventListener("click", function (event) {
        const removeButton = event.target.closest(".remove-participant-button");

        if (!removeButton) {
            return;
        }

        const participants = wrapper.querySelectorAll(".participant-item");

        if (participants.length <= 1) {
            return;
        }

        removeButton.closest(".participant-item").remove();
        refreshParticipants();
        saveOrderDraft();
    });

    wrapper.addEventListener("input", function (event) {
        if (!event.target.matches("input")) {
            return;
        }

        event.target.classList.remove("field-error");
        event.target.removeAttribute("aria-invalid");

        const participantItem = event.target.closest(".participant-item");

        if (participantItem) {
            participantItem.classList.remove("participant-card--error");
        }

        if (event.target.matches('input[name$="-email"]')) {
            const emailError = participantItem
                ? participantItem.querySelector("[data-participant-email-error]")
                : null;

            if (emailError) {
                emailError.textContent = "";
                emailError.hidden = true;
            }
        }

        clearValidationMessage(participantsErrorMessage);
        saveOrderDraft();
    });

    document.querySelectorAll(".billing-grid input, .billing-grid textarea, .billing-grid select").forEach(function (input) {
        input.addEventListener("input", function () {
            input.classList.remove("field-error");
            clearValidationMessage(billingErrorMessage);
            saveOrderDraft();
        });

        input.addEventListener("change", function () {
            saveOrderDraft();
        });
    });

    refreshParticipants();

    const existingDraft = getOrderDraft();

    if (existingDraft && existingDraft.selected_course && courses[existingDraft.selected_course]) {
        restoreOrderDraft();
    } else {
        showStep(1);
    }

    if (hasParticipantServerErrors) {
        showStep(3);
    } else if (hasBillingServerErrors) {
        showStep(4);
    }

    function deleteDraftOrder() {
        const confirmed = confirm(
            "Opravdu chcete zrušit rozpracovanou objednávku?"
        );

        if (!confirmed) {
            return;
        }

        ORDER_DRAFT_KEYS.forEach(function (key) {
            localStorage.removeItem(key);
        });

        window.location.href = registrationForm.dataset.indexUrl;
    }

    document.querySelectorAll(".delete-order-button").forEach(function (button) {
        button.addEventListener("click", deleteDraftOrder);
    });

    if (registrationForm && termsAgreement && termsAgreementLabel) {
        registrationForm.addEventListener("submit", function (event) {

            if (!termsAgreement.checked) {
                event.preventDefault();

                termsAgreementLabel.classList.add("error");

                termsAgreement.scrollIntoView({
                    behavior: "smooth",
                    block: "center"
                });

                termsAgreement.focus();
                return;
            }

            termsAgreementLabel.classList.remove("error");
        });

        termsAgreement.addEventListener("change", function () {
            if (termsAgreement.checked) {
                termsAgreementLabel.classList.remove("error");
            }
        });
    }

});
