

function setDropdownValue(selectId, value) {
    let selectElement = document.getElementById(selectId);
    if (selectElement) {
        let optionExists = Array.from(selectElement.options).some(option => option.value === value);
        if (optionExists) {
            selectElement.value = value;
        } else {
            console.warn(`Value "${value}" not found in #${selectId}`);
        }
    } else {
        console.error(`Dropdown #${selectId} not found`);
    }
}


function setEndingTimeNow() {
    const now = new Date();
    const formattedDate = now.toISOString().slice(0, 16); // Format YYYY-MM-DDTHH:MM
    document.getElementById("ending_time").value = formattedDate;
}


function getLabel(value, choices) {
    return choices[value] || value; // Fallback to the raw value if not found
}

function formatDuration(start, end) {
    if (!start || !end) return "0sec"; // Default to 0 seconds if data is missing

    const startDate = new Date(start);
    const endDate = new Date(end);
    let totalSeconds = Math.floor((endDate - startDate) / 1000);

    if (totalSeconds <= 0) return "0sec";

    const weeks = Math.floor(totalSeconds / (7 * 24 * 60 * 60));
    totalSeconds %= 7 * 24 * 60 * 60;
    
    const days = Math.floor(totalSeconds / (24 * 60 * 60));
    totalSeconds %= 24 * 60 * 60;

    const hours = Math.floor(totalSeconds / (60 * 60));
    totalSeconds %= 60 * 60;

    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;

    const parts = [];
    if (weeks > 0) parts.push(`${weeks}w`);
    if (days > 0) parts.push(`${days}d`);
    if (hours > 0) parts.push(`${hours}h`);
    if (minutes > 0) parts.push(`${minutes}min`);
    if (seconds > 0 && parts.length === 0) parts.push(`${seconds}sec`); // Include seconds only if no other units

    return parts.join(" ") || "0sec";
}
