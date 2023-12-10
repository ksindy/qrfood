const calendar = document.getElementById('calendar');
const monthTallies = { '2023-03-01': 2, '2023-03-15': 5 }; // Example JSON data

function generateCalendar() {
    // Assuming you have a function to get all days in a month
    const daysInMonth = getDaysInMonth(); // Implement this

    daysInMonth.forEach(day => {
        const dayElement = document.createElement('div');
        dayElement.classList.add('day');
        dayElement.textContent = day.getDate();

        // If the day has a tally
        const dateStr = day.toISOString().split('T')[0];
        if (monthTallies[dateStr]) {
            dayElement.textContent += ` (${monthTallies[dateStr]})`;
        }

        dayElement.addEventListener('click', () => incrementTally(dateStr));
        calendar.appendChild(dayElement);
    });
}

function incrementTally(dateStr) {
    if (!monthTallies[dateStr]) {
        monthTallies[dateStr] = 0;
    }
    monthTallies[dateStr]++;
    updateCalendar(); // Redraw the calendar to reflect the new tallies
}

function updateCalendar() {
    // Clear the current calendar and regenerate it
    calendar.innerHTML = '';
    generateCalendar();
}

generateCalendar();
