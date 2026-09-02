document.addEventListener('DOMContentLoaded', function () {
    const root = document.documentElement;
    const topbar = document.querySelector('.topbar');
    const pageScroll = document.querySelector('.page-scroll');

    const landingNavLinks = document.querySelectorAll('.landing-nav-link');
    const sections = document.querySelectorAll('.page-section[id]');
    const faqList = document.querySelector('#faq .faq-list');
    const contactSection = document.getElementById('contact');
    let faqExitLocked = false;

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
        link.addEventListener('click', function (e) {
            e.preventDefault();

            const targetId = link.dataset.target;
            const target = document.getElementById(targetId);

            if (!target) return;

            scrollToSection(target);
            setActiveLandingNav(targetId);
        });
    });

    document.querySelectorAll('a[href^="#"]').forEach(link => {
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

    /* FAQ TOP EXIT v21 — další scroll nahoru přejde na Kontakt */
    if (faqList && contactSection) {
        faqList.addEventListener('wheel', function (e) {
            const isAtTop = faqList.scrollTop <= 1;
            const isScrollingUp = e.deltaY < 0;

            if (!isAtTop || !isScrollingUp) return;

            e.preventDefault();
            e.stopPropagation();

            if (faqExitLocked) return;
            faqExitLocked = true;

            scrollToSection(contactSection);
            setActiveLandingNav('contact');

            window.setTimeout(function () {
                faqExitLocked = false;
            }, 900);
        }, { passive: false });
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

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') closeVideoModal();
    });
});
