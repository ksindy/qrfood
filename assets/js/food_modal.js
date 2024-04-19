document.querySelectorAll('.item-link').forEach(function(link) {
    link.addEventListener('click', function(event) {
        event.preventDefault(); 
        const itemFood = this.getAttribute('data-item-food');
        let itemImage = this.getAttribute('data-item-image');
        const itemLocation = this.getAttribute('data-item-location');
        const itemExpiration = this.getAttribute('data-item-expiration');

       // Check if itemImage is "None" and set it to the fallback URL
       if (!itemImage || itemImage === "None") {
        itemImage = 'https://qr-app-images-dev.s3.us-east-2.amazonaws.com/default_food_photo.jpeg';
        }

        // Set the modal title and other fields
        document.querySelector("#modal-1 .modal-title").textContent = itemFood;
        document.querySelector("#modal-1 .modal-body input[type='text']").value = itemFood;
        document.getElementById('modalFoodDate').value = itemExpiration;

        // Set the image source in the modal
        const modalImage = document.querySelector("#modal-1 .modal-body img");
        modalImage.src = itemImage;
        modalImage.alt = itemFood + " Image";

        // Optionally, set the location if needed
        const locationDropdown = document.querySelector("#modal-1 .modal-body select");
        locationDropdown.value = itemLocation;

        // Calculate the time until expiration and update the text area
        const expirationDate = new Date(itemExpiration);
        const today = new Date();
        const diffTime = Math.abs(expirationDate - today);
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        const years = Math.floor(diffDays / 365);
        let remainingDays = diffDays % 365;
        const months = Math.floor(remainingDays / 30);
        remainingDays = remainingDays % 30;

        // Dynamic singular or plural based on the count
        const yearText = years === 1 ? 'year' : 'years';
        const monthText = months === 1 ? 'month' : 'months';
        const dayText = remainingDays === 1 ? 'day' : 'days';

        // Building the display text
        let displayText = '';
        if (years > 0) {
            displayText += `${years} ${yearText}, `;
        }
        if (months > 0) {
            displayText += `${months} ${monthText}, `;
        }
        if (remainingDays > 0) {
            displayText += `${remainingDays} ${dayText}`;
        }
        if (displayText.endsWith(', ')) {
            displayText = displayText.slice(0, -2);  // Remove the last comma if exists
        }

        // Set the calculated difference into the text area
        document.getElementById('modalExpirationDetails').value = displayText + ' until expiration:';
    });
});
