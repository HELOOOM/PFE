document.addEventListener("DOMContentLoaded", function () {
    let slides = document.querySelectorAll(".slide");
    let index = 0;
    let totalSlides = slides.length;

    // Assurez-vous que seul le premier slide est visible au début
    slides.forEach((slide, i) => {
        slide.style.display = i === 0 ? "block" : "none";
    });

    function changeSlide() {
        // Masquer l'image actuelle
        slides[index].style.display = "none";

        // Passer à l'image suivante (de manière circulaire)
        index = (index + 1) % totalSlides;

        // Afficher la nouvelle image
        slides[index].style.display = "block";
    }

    setInterval(changeSlide, 4000); // Changement toutes les 4 secondes
});
