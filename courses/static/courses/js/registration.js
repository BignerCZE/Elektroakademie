document.addEventListener("DOMContentLoaded", function () {
    const orderDraftStorage = window.ElektroakademieOrderDraft;
    const ORDER_DRAFT_KEY = orderDraftStorage.currentKey;
    const registrationForm = document.getElementById("registration-form");
    const courses = {
        "4": {
            title: "Zkouška odborné způsobilosti §4 – osoba poučená",
            shortTitle: "§4 – osoba poučená",
            meta: "Online školení",
            price: 990,
            orderMode: "standard",
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
            orderMode: "contact",
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
            orderMode: "contact",
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
    const checkoutBackButton = document.getElementById("checkout-back-button");
    const goToParticipantsButton = document.getElementById("go-to-participants-button");
    const participantsToBillingButton = document.getElementById("participants-to-billing-button");
    const participantsErrorMessage = document.getElementById("participants-error-message");
    const billingErrorMessage = document.getElementById("billing-error-message");
    const termsAgreement = document.getElementById("terms-agreement");
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
        return String(value || "").trim();
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
        clearFieldError(icoInput);

        if (!/^[0-9]{8}$/.test(ico)) {
            showFieldError(icoInput, ["IČO musí obsahovat přesně 8 číslic."]);
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
    const courseInfoActionTitle = document.getElementById("course-info-action-title");
    const courseInfoActionText = document.getElementById("course-info-action-text");
    const orderSummaryCard = document.getElementById("order-summary-card");
    const finalOrderActionCard = document.getElementById("final-order-action-card");
    const mobileCheckoutNextButton = document.createElement("button");
    mobileCheckoutNextButton.type = "button";
    mobileCheckoutNextButton.id = "mobile-checkout-next-button";
    mobileCheckoutNextButton.className = "mobile-checkout-next-button";
    mobileCheckoutNextButton.hidden = true;

    if (checkoutBackButton && checkoutBackButton.parentNode) {
        checkoutBackButton.parentNode.insertBefore(mobileCheckoutNextButton, checkoutBackButton);
    }

    function getMobileCheckoutTarget(step) {
        if (step === 2) return goToParticipantsButton;
        if (step === 3) return participantsToBillingButton;
        if (step === 4) return goToFinalSummaryButton;
        if (step === 5 && finalOrderActionCard) {
            return finalOrderActionCard.querySelector('button[type="submit"], input[type="submit"]');
        }
        return null;
    }

    function updateMobileCheckoutAction(step) {
        const target = getMobileCheckoutTarget(step);

        if (!target) {
            mobileCheckoutNextButton.hidden = true;
            mobileCheckoutNextButton.disabled = false;
            mobileCheckoutNextButton.textContent = "";
            return;
        }

        mobileCheckoutNextButton.hidden = false;
        mobileCheckoutNextButton.disabled = Boolean(target.disabled);
        mobileCheckoutNextButton.textContent =
            (target.textContent || target.value || "Pokračovat").trim();
    }

    mobileCheckoutNextButton.addEventListener("click", function () {
        const step = Number(document.body.dataset.checkoutStep || "1");
        const target = getMobileCheckoutTarget(step);

        if (target && !target.disabled) {
            target.click();
        }
    });

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

    function isStandardOrderCourse(courseId) {
        return Boolean(courses[courseId] && courses[courseId].orderMode === "standard");
    }

    function isContactCourse(courseId) {
        return Boolean(courses[courseId] && courses[courseId].orderMode === "contact");
    }

    function getRequestedCourseId() {
        const courseId = new URLSearchParams(window.location.search).get("course");
        return courseId && courses[courseId] ? courseId : null;
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

        if (!isStandardOrderCourse(courseId)) {
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
            input.removeAttribute("aria-invalid");
            input.removeAttribute("aria-describedby");
            input.value = "";
        });

        newParticipant.querySelectorAll(".errorlist, .checkout-field-error").forEach(function (errorList) {
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
            const participantsToRestore = draft.participants;

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
            if (restoredStep >= 4) {
                (async function () {
                    if (!(await validateOrder(3))) return;
                    if (restoredStep === 5) await validateOrder(4);
                })();
            }
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
    // Every step uses the same Django forms as the final POST. In particular,
    // HTML email validity and Django EmailValidator need not accept the same input.
    const orderErrorMessage = document.getElementById("order-error-message");
    let validationInProgress = false;
    let validationRevision = 0;
    let submitted = false;

    function fieldStep(name) {
        return name.startsWith("participants-") ? 3 : name === "terms_agreement" ? 5 : 4;
    }

    function clearFieldError(input) {
        if (!input) return;
        input.classList.remove("field-error");
        input.removeAttribute("aria-invalid");
        const errorId = input.id + "-validation-error";
        document.getElementById(errorId)?.remove();
        const describedBy = (input.getAttribute("aria-describedby") || "")
            .split(/\s+/).filter(id => id && id !== errorId);
        if (describedBy.length) input.setAttribute("aria-describedby", describedBy.join(" "));
        else input.removeAttribute("aria-describedby");
    }

    function showFieldError(input, messages) {
        clearFieldError(input);
        input.classList.add("field-error");
        input.setAttribute("aria-invalid", "true");
        const error = document.createElement("div");
        error.id = input.id + "-validation-error";
        error.className = "checkout-field-error";
        error.textContent = messages.join(" ");
        const anchor = input.closest(".ares-input-group") || (input.type === "checkbox" ? input.closest("label") : null) || input;
        anchor.insertAdjacentElement("afterend", error);
        input.setAttribute("aria-describedby", [input.getAttribute("aria-describedby"), error.id].filter(Boolean).join(" "));
    }

    function focusProblem(input, step) {
        // Reveal before focusing: hidden controls cannot receive browser focus.
        showStep(step);
        const target = input || orderErrorMessage;
        target.focus({ preventScroll: true });
        target.scrollIntoView({ block: "center", behavior: "smooth" });
    }

    function displayErrors(result, focus = true) {
        registrationForm.querySelectorAll(".errorlist, [data-participant-email-error]")
            .forEach(element => { element.hidden = true; });
        document.querySelectorAll("#final-order-action-card .errorlist").forEach(element => { element.hidden = true; });
        Array.from(registrationForm.elements).forEach(clearFieldError);
        clearValidationMessage(participantsErrorMessage);
        clearValidationMessage(billingErrorMessage);
        clearValidationMessage(orderErrorMessage);
        orderErrorMessage.dataset.globalError = (result.global || []).length ? "true" : "";
        const problems = [];
        for (const [name, messages] of Object.entries(result.fields || {})) {
            const input = registrationForm.elements.namedItem(name);
            if (input && input.type !== "hidden") {
                showFieldError(input, messages);
                problems.push({ step: fieldStep(name), input });
            } else {
                // Management-form errors have no visible control.
                result.global = [...(result.global || []), {step: 3, message: messages.join(" ")}];
            }
        }
        for (const error of result.global || []) problems.push({step: error.step, input: null});
        problems.sort((a, b) => a.step - b.step);
        if (problems.length) {
            showValidationMessage(orderErrorMessage, "Objednávku je potřeba opravit.",
                (result.global || []).length ? result.global.map(error => error.message) : ["Opravte označená pole a pokračujte znovu."]);
            if (focus) focusProblem(problems[0].input, problems[0].step);
        }
        return !problems.length;
    }

    async function validateOrder(step) {
        if (validationInProgress || submitted) return false;
        validationInProgress = true;
        const revision = validationRevision;
        const data = new FormData(registrationForm);
        data.set("_validate_step", String(step));
        const buttons = [participantsToBillingButton, goToFinalSummaryButton,
            finalOrderActionCard.querySelector('[type="submit"]')];
        buttons.forEach(button => { button.disabled = true; });
        registrationForm.setAttribute("aria-busy", "true");
        const status = document.getElementById("order-validation-status");
        status.hidden = false;
        status.textContent = "Kontroluji údaje…";
        const controller = new AbortController();
        const timeout = window.setTimeout(() => controller.abort(), 15000);
        try {
            const response = await fetch(registrationForm.action || window.location.href, {
                method: "POST", body: data, signal: controller.signal, headers: {"Accept": "application/json"}
            });
            if (!response.ok) throw new Error("Kontrola se nezdařila. Zkuste pokračovat znovu; při vypršení přihlášení obnovte stránku.");
            const result = await response.json();
            if (typeof result.valid !== "boolean" || !result.fields || !Array.isArray(result.global)) {
                throw new Error("Server nevrátil výsledek kontroly.");
            }
            if (revision !== validationRevision) {
                showValidationMessage(orderErrorMessage, "Údaje se během kontroly změnily.", ["Pokračujte znovu pro kontrolu aktuálních hodnot."]);
                return false;
            }
            displayErrors(result);
            return result.valid === true;
        } catch (error) {
            showValidationMessage(orderErrorMessage, "Kontrolu objednávky nelze dokončit.",
                [error.name === "AbortError" ? "Kontrola trvá příliš dlouho. Zkuste pokračovat znovu." : "Zkontrolujte připojení a zkuste pokračovat znovu."]);
            orderErrorMessage.focus();
            orderErrorMessage.scrollIntoView({block: "center"});
            return false;
        } finally {
            window.clearTimeout(timeout);
            status.hidden = true;
            validationInProgress = false;
            buttons.forEach(button => { button.disabled = false; });
            registrationForm.removeAttribute("aria-busy");
        }
    }

    // Editing invalid values removes the obsolete server message. The next
    // Continue/Submit always revalidates; unrelated field errors stay visible.
    function onOrderEdit(event) {
        if (!event.target.matches("input, select, textarea")) return;
        validationRevision += 1;
        clearFieldError(event.target);
        if (!document.querySelector(".checkout-field-error") && !orderErrorMessage.dataset.globalError) clearValidationMessage(orderErrorMessage);
        saveOrderDraft();
    }
    registrationForm.addEventListener("input", onOrderEdit);
    registrationForm.addEventListener("change", onOrderEdit);
    termsAgreement.addEventListener("change", onOrderEdit);

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

    function updateCourseActionPanel(courseId) {
        if (!courseInfoActionTitle || !courseInfoActionText || !goToParticipantsButton) {
            return;
        }

        if (isContactCourse(courseId)) {
            courseInfoActionTitle.textContent = "Individuální průběh školení";
            courseInfoActionText.textContent =
                "Toto školení aktuálně probíhá individuální formou. Pro domluvení termínu a dalších podrobností nás kontaktujte prostřednictvím kontaktního formuláře.";
            goToParticipantsButton.textContent = "Přejít na kontaktní formulář";
            return;
        }

        courseInfoActionTitle.textContent = "Pokračovat";
        courseInfoActionText.textContent =
            "Po přečtení informací pokračujte k zadání účastníků školení.";
        goToParticipantsButton.textContent = "Přejít k objednávce";
    }

    function showStep(step) {
        const selectedCourseId = selectedCourseInput.value;

        if (isContactCourse(selectedCourseId) && step >= 3) {
            step = 2;
        }

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
        finalOrderActionCard.hidden = step !== 5;
        participantsToBillingButton.hidden = step !== 3;
        goToFinalSummaryButton.hidden = step !== 4;
        updateMobileCheckoutAction(step);

        if (finalSummaryConsentInput) {
            finalSummaryConsentInput.disabled = step !== 5;
        }
        if (step === 5) {
            renderFinalSummary();
        }

        if (isStandardOrderCourse(selectedCourseId) && step >= 2) {
            const draft = getOrderDraft();

            if (draft && draft.selected_course === selectedCourseId) {
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
        updateCourseActionPanel(courseId);

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
            // Django formsets consume exactly 0..TOTAL_FORMS-1. Reindex every
            // reference after deleting a row, including accessible labels.
            [participant, ...participant.querySelectorAll("*")].forEach(function (element) {
                ["name", "id", "for", "aria-describedby", "aria-labelledby", "aria-controls"].forEach(function (attribute) {
                    const value = element.getAttribute(attribute);
                    if (value) {
                        element.setAttribute(attribute, value.replace(/participants-\d+-/g, "participants-" + index + "-"));
                    }
                });
            });
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

            if (validationInProgress) return;
            validationRevision += 1;
            updateCourseView(courseId);
            saveOrderDraft();
            showStep(2);
            window.scrollTo({ top: 0, behavior: "smooth" });
        });
    });
    if (goToParticipantsButton) {
        goToParticipantsButton.addEventListener("click", function () {
            const courseId = selectedCourseInput.value;

            if (isContactCourse(courseId)) {
                window.location.href = registrationForm.dataset.contactUrl;
                return;
            }

            if (!isStandardOrderCourse(courseId)) {
                return;
            }

            saveOrderDraft();
            showStep(3);
            window.scrollTo({ top: 0, behavior: "smooth" });
        });
    }

    participantsToBillingButton.addEventListener("click", async function () {
        if (!(await validateOrder(3))) return;
        saveOrderDraft();
        showStep(4);
        window.scrollTo({top: 0, behavior: "smooth"});
    });
    goToFinalSummaryButton.addEventListener("click", async function () {
        if (!(await validateOrder(4))) return;
        saveOrderDraft();
        showStep(5);
        window.scrollTo({top: 0, behavior: "smooth"});
    });
    [
        goToParticipantsButton,
        participantsToBillingButton,
        goToFinalSummaryButton
    ].filter(Boolean).forEach(function (button) {
        new MutationObserver(function () {
            updateMobileCheckoutAction(Number(document.body.dataset.checkoutStep || "1"));
        }).observe(button, {
            attributes: true,
            childList: true,
            subtree: true
        });
    });

    if (finalOrderActionCard) {
        new MutationObserver(function () {
            updateMobileCheckoutAction(Number(document.body.dataset.checkoutStep || "1"));
        }).observe(finalOrderActionCard, {
            attributes: true,
            childList: true,
            subtree: true
        });
    }

    if (addButton) {
        addButton.addEventListener("click", function () {
            validationRevision += 1;
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
            const courseId = selectedCourseInput.value;

            if (step > 1 && !courseId) {
                showStep(1);
                return;
            }

            if (isContactCourse(courseId) && step >= 3) {
                showStep(2);
                return;
            }
            if (validationInProgress) return;
            if (step >= 4 && !(await validateOrder(3))) return;
            if (step === 5 && !(await validateOrder(4))) return;
            saveOrderDraft();
            showStep(step);
            window.scrollTo({ top: 0, behavior: "smooth" });
        });
    });

    checkoutBackButton.addEventListener("click", function () {
        if (validationInProgress) return;
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
        validationRevision += 1;
        removeButton.closest(".participant-item").remove();
        refreshParticipants();
        saveOrderDraft();
    });

    refreshParticipants();

    const existingDraft = getOrderDraft();
    const requestedCourseId = getRequestedCourseId();
    if (registrationForm.dataset.bound === "true") {
        // A rejected POST is authoritative; never overwrite it with localStorage.
        if (courses[selectedCourseInput.value]) updateCourseView(selectedCourseInput.value);
        showStep(Number(registrationForm.dataset.initialStep));
        displayErrors(JSON.parse(document.getElementById("registration-errors").textContent));
        saveOrderDraft();
    } else if (existingDraft && existingDraft.selected_course && courses[existingDraft.selected_course]
        && (!requestedCourseId || requestedCourseId === existingDraft.selected_course)) {
        restoreOrderDraft();
    } else if (requestedCourseId) {
        updateCourseView(requestedCourseId);
        showStep(2);
        saveOrderDraft();
    } else {
        showStep(1);
    }
    function returnToOrderStart() {
        if (validationInProgress) return;
        showStep(1);
        saveOrderDraft();

        const checkoutShell = document.querySelector(".register-checkout-shell");
        if (checkoutShell) {
            checkoutShell.scrollIntoView({ behavior: "smooth", block: "start" });
        }
    }

    document.querySelectorAll(".restart-order-button").forEach(function (button) {
        button.addEventListener("click", returnToOrderStart);
    });
    registrationForm.addEventListener("submit", async function (event) {
        event.preventDefault();
        if (isContactCourse(selectedCourseInput.value)) {
            window.location.href = registrationForm.dataset.contactUrl;
            return;
        }
        if (!(await validateOrder("all"))) return;
        saveOrderDraft();
        submitted = true;
        // Bypass native constraint validation only after every server-backed
        // check passed. The final POST independently validates everything again.
        HTMLFormElement.prototype.submit.call(registrationForm);
    });

});
