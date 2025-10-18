// Global variable to track if images have been updated
let imageUpdated = false;
let originalImages = [];

// Function to capture current captcha images
function captureCurrentImages() {
    const images = [];
    const tableCells = document.querySelectorAll('table td');
    
    tableCells.forEach((cell, index) => {
        const img = cell.querySelector('img');
        if (img && img.src) {
            images.push({
                index: index,
                src: img.src
            });
        }
    });
    
    return images; 
}

// Function to check if images have changed
function haveImagesChanged() {
    const currentImages = captureCurrentImages();
    
    if (originalImages.length === 0) {
        originalImages = currentImages;
        return false;
    }
    
    if (currentImages.length !== originalImages.length) {
        return true;
    }
    
    for (let i = 0; i < currentImages.length; i++) {
        if (currentImages[i].src !== originalImages[i].src) {
            return true;
        }
    }
    
    return false;
}

// Main monitoring function
window.monitorRequests = () => {
    // Reset the flag
    imageUpdated = false;
    
    // Capture initial images
    originalImages = captureCurrentImages();
    
    // Monitor for network requests
    const observer = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        entries.forEach((entry) => {
            if (entry.initiatorType === 'xmlhttprequest' || 
                entry.initiatorType === 'fetch') {
                const url = new URL(entry.name);
                if (url.href.includes("recaptcha/api2/replaceimage") || 
                    url.href.includes("recaptcha/api2/payload")) {
                    imageUpdated = true;
                }
            }
        });
    });
    
    observer.observe({ entryTypes: ['resource'] });
    
    // Also monitor DOM mutations as a fallback
    const mutationObserver = new MutationObserver(() => {
        if (haveImagesChanged()) {
            imageUpdated = true;
        }
    });
    
    const table = document.querySelector('table');
    if (table) {
        mutationObserver.observe(table, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['src']
        });
    }
    
    // Return promise that resolves after a short delay
    return new Promise((resolve) => {
        setTimeout(() => {
            // Final check using image comparison
            if (haveImagesChanged()) {
                imageUpdated = true;
            }
            resolve(imageUpdated);
        }, 2000); // Reduced timeout for faster detection
    });
};