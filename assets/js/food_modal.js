document.querySelectorAll('.item-link').forEach(function(link) {
    link.addEventListener('click', function(event) {
        event.preventDefault(); 
        const itemFood = this.getAttribute('data-item-food');
        let itemImage = this.getAttribute('data-item-image');
        const itemLocation = this.getAttribute('data-item-location');

       // Check if itemImage is "None" and set it to the fallback URL
       if (!itemImage || itemImage === "None") {
        itemImage = 'https://qr-app-images-dev.s3.us-east-2.amazonaws.com/default_food_photo.jpeg';
        }

        // Set the modal title and other fields
        document.querySelector("#modal-1 .modal-title").textContent = "Modify Food Details: " + itemFood;
        document.querySelector("#modal-1 .modal-body input[type='text']").value = itemFood;

        // Set the image source in the modal
        const modalImage = document.querySelector("#modal-1 .modal-body img");
        modalImage.src = itemImage;
        modalImage.alt = itemFood + " Image";

        // Optionally, set the location if needed
        const locationDropdown = document.querySelector("#modal-1 .modal-body select");
        locationDropdown.value = itemLocation;
    });
});
