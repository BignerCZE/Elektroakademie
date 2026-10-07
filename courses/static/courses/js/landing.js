document.addEventListener('DOMContentLoaded', function () {
    const root = document.documentElement;
    const topbar = document.querySelector('.topbar');
    const pageScroll = document.querySelector('.page-scroll');

    const landingNavLinks = document.querySelectorAll('.landing-nav-link');
    const sections = document.querySelectorAll('.page-section[id]');

    const faqModal = document.getElementById('faq');
    const faqModalLinks = document.querySelectorAll('a[href="#faq"], a[href$="/#faq"]');
    const faqModalCloseButtons = document.querySelectorAll('[data-faq-modal-close]');
    const faqQuestions = document.querySelectorAll('.faq-question');
    let faqModalTrigger = null;

    const homeLink = document.getElementById('home-link');
    const introSection = document.getElementById('intro');

    const openVideoModalButton = document.getElementById('open-video-modal');
    const videoModal = document.getElementById('video-modal');
    const closeVideoModalBackdrop = document.getElementById('close-video-modal');
    const closeVideoModalButton = document.getElementById('video-modal-close');
    const videoModalFrame = document.getElementById('video-modal-frame');

    const programTabs = document.querySelectorAll('.program-tab');
    const programPanels = document.querySelectorAll('.program-panel');
    const programLinks = document.querySelectorAll('[data-program-link]');

    function setHeaderHeight() {
        if (topbar) {
            root.style.setProperty('--header-height', `${topbar.offsetHeight}px`);
        }
    }

    function scrollToSection(target) {
        if (!pageScroll || !target) return;

        const isMobile = window.innerWidth <= 768;
        const offset = isMobile ? 40 : 0;

        const targetTop =
            target.getBoundingClientRect().top
            - pageScroll.getBoundingClientRect().top
            + pageScroll.scrollTop;

        pageScroll.scrollTo({
            top: targetTop - offset,
            behavior: 'smooth'
        });
    }

    function setActiveLandingNav(sectionId) {
        landingNavLinks.forEach(link => {
            link.classList.toggle('is-active', link.dataset.target === sectionId);
        });
    }

    function updateActiveSection() {
        if (!pageScroll || !sections.length) return;

        let activeSectionId = sections[0].id;
        const scrollMiddle = pageScroll.scrollTop + pageScroll.clientHeight / 2;

        sections.forEach(section => {
            if (section.offsetTop <= scrollMiddle) {
                activeSectionId = section.id;
            }
        });

        setActiveLandingNav(activeSectionId);
    }

    function activateProgram(targetId) {
        const targetPanel = document.getElementById(targetId);
        const targetTab = document.querySelector(`.program-tab[data-program="${targetId}"]`);

        if (!targetPanel || !targetTab) return;

        programTabs.forEach(tab => {
            tab.classList.remove('is-active');
            tab.setAttribute('aria-selected', 'false');
        });

        programPanels.forEach(panel => {
            panel.classList.remove('is-active');
        });

        targetTab.classList.add('is-active');
        targetTab.setAttribute('aria-selected', 'true');
        targetPanel.classList.add('is-active');
    }

    function openVideoModal() {
        if (!videoModal || !videoModalFrame) return;

        videoModal.classList.add('is-open');
        videoModal.setAttribute('aria-hidden', 'false');

        videoModalFrame.innerHTML = `
            <iframe
                src="https://www.youtube.com/embed/LDU_Txk06tM?autoplay=1&rel=0&modestbranding=1"
                title="YouTube video player"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                referrerpolicy="strict-origin-when-cross-origin"
                allowfullscreen>
            </iframe>
        `;
    }

    function closeVideoModal() {
        if (!videoModal || !videoModalFrame) return;

        videoModal.classList.remove('is-open');
        videoModal.setAttribute('aria-hidden', 'true');
        videoModalFrame.innerHTML = '';
    }

    function openFaqModal(trigger) {
        if (!faqModal) return;

        faqModalTrigger = trigger || document.activeElement;
        faqModal.classList.add('is-open');
        faqModal.setAttribute('aria-hidden', 'false');
        document.body.classList.add('faq-modal-open');
        setActiveLandingNav('faq');

        if (window.location.hash !== '#faq') {
            window.history.replaceState(null, '', '#faq');
        }

        const closeButton = faqModal.querySelector('[data-faq-modal-close]');
        if (closeButton) closeButton.focus();
    }

    function closeFaqModal() {
        if (!faqModal || !faqModal.classList.contains('is-open')) return;

        faqModal.classList.remove('is-open');
        faqModal.setAttribute('aria-hidden', 'true');
        document.body.classList.remove('faq-modal-open');

        if (window.location.hash === '#faq') {
            window.history.replaceState(null, '', window.location.pathname + window.location.search);
        }

        updateActiveSection();

        if (faqModalTrigger && typeof faqModalTrigger.focus === 'function') {
            faqModalTrigger.focus();
        }
        faqModalTrigger = null;
    }

    function toggleFaqAnswer(question) {
        const answerId = question.getAttribute('aria-controls');
        const answer = document.getElementById(answerId);
        if (!answer) return;

        const willOpen = question.getAttribute('aria-expanded') !== 'true';

        faqQuestions.forEach(otherQuestion => {
            const otherAnswer = document.getElementById(otherQuestion.getAttribute('aria-controls'));
            otherQuestion.setAttribute('aria-expanded', 'false');
            if (otherAnswer) otherAnswer.hidden = true;
        });

        question.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
        answer.hidden = !willOpen;
    }

    programTabs.forEach(tab => {
        tab.addEventListener('click', function () {
            activateProgram(tab.dataset.program);
        });
    });

    programLinks.forEach(link => {
        link.addEventListener('click', function (e) {
            e.preventDefault();

            const targetProgram = link.dataset.programLink;
            const targetSection = document.getElementById('programs');

            activateProgram(targetProgram);

            if (targetSection) {
                scrollToSection(targetSection);
                setActiveLandingNav('programs');
            }
        });
    });

    setHeaderHeight();
    updateActiveSection();

    window.addEventListener('resize', function () {
        setHeaderHeight();
        updateActiveSection();
    });

    landingNavLinks.forEach(link => {
        if (link.hasAttribute('data-faq-modal-open')) return;

        link.addEventListener('click', function (e) {
            e.preventDefault();

            const targetId = link.dataset.target;
            const target = document.getElementById(targetId);

            if (!target) return;

            scrollToSection(target);
            setActiveLandingNav(targetId);
        });
    });

    document.querySelectorAll('a[href^="#"]:not(.landing-nav-link):not([href="#faq"])').forEach(link => {
        link.addEventListener('click', function (e) {
            e.preventDefault();

            const targetId = link.getAttribute('href').replace('#', '');
            const target = document.getElementById(targetId);

            if (!target) return;

            scrollToSection(target);
            setActiveLandingNav(targetId);
        });
    });

    if (pageScroll) {
        pageScroll.addEventListener('scroll', updateActiveSection);
    }

    if (homeLink && introSection) {
        homeLink.addEventListener('click', function (e) {
            e.preventDefault();
            scrollToSection(introSection);
            setActiveLandingNav('intro');
        });
    }

    if (openVideoModalButton) openVideoModalButton.addEventListener('click', openVideoModal);
    if (closeVideoModalBackdrop) closeVideoModalBackdrop.addEventListener('click', closeVideoModal);
    if (closeVideoModalButton) closeVideoModalButton.addEventListener('click', closeVideoModal);

    faqModalLinks.forEach(link => {
        link.addEventListener('click', function (e) {
            e.preventDefault();
            openFaqModal(link);
        });
    });

    faqModalCloseButtons.forEach(button => {
        button.addEventListener('click', closeFaqModal);
    });

    faqQuestions.forEach(question => {
        question.addEventListener('click', function () {
            toggleFaqAnswer(question);
        });
    });

    if (faqModal) {
        faqModal.addEventListener('click', function (e) {
            if (e.target === faqModal) closeFaqModal();
        });
    }

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
            closeVideoModal();
            closeFaqModal();
        }
    });

    if (window.location.hash === '#faq') {
        openFaqModal();
    }

    window.addEventListener('hashchange', function () {
        if (window.location.hash === '#faq') openFaqModal();
    });
});
