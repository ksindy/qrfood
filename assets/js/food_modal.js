document.addEventListener('DOMContentLoaded', function() {
    // Attach click event listener to each item link
    document.querySelectorAll('.item-link').forEach(function(link) {
        link.addEventListener('click', function() {
            // Retrieve item data from data attributes
            const itemId = this.getAttribute('data-item-id');
            const itemFood = this.getAttribute('data-item-food');
            const itemImage = this.getAttribute('data-item-image');
            const itemExpiration = this.getAttribute('data-item-expiration');
            const itemLocation = this.getAttribute('data-item-location');
            
            // Populate the modal with the retrieved item data
            document.querySelector("#modal-1 .modal-title").textContent = "Modify Food Details: " + itemFood;
            document.querySelector("#modal-1 .modal-body img").src = itemImage;
            document.querySelector("#modal-1 .modal-body img").alt = itemFood + " Image";
            document.querySelector("#modal-1 .modal-body input[type='text']").value = itemFood;
            // Set the expiration date if your form has a field for it
            // Example: document.querySelector("#modal-1 .modal-body input[type='date']").value = itemExpiration;
            // Set the dropdown to the chosen location
            const locationDropdown = document.querySelector("#modal-1 .modal-body select");
            locationDropdown.value = itemLocation; // This assumes the location value matches one of the options

        });
    });
});


