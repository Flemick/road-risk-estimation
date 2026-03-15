let map;
let routeLayer;
let highlightLayer;
let currentRouteCoords = [];
let currentUser = null;

function initMap() {
    map = L.map('map').setView([10.8505, 76.2711], 7);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);
}

// -------- BUILD SEGMENTS FROM ROUTE --------
function buildRouteSegments(coords) {
    const segments = [];
    const STEP = 20;

    for (let i = 0; i < coords.length; i += STEP) {
        const coord = coords[i];
        segments.push({
            lat: coord[1],
            lon: coord[0],
            road_type: "urban",
            time_of_day: getTimeOfDay(),
            weather: "clear"
        });
    }
    return segments;
}

// -------- DETECT TIME OF DAY --------
function getTimeOfDay() {
    const hour = new Date().getHours();
    if (hour < 6) return "night";
    if (hour < 12) return "morning";
    if (hour < 18) return "evening";
    return "night";
}

async function geocodeLocation(place) {
    try {
        // Automatically contextualize the search to Thrissur for the demo
        const searchQuery = place.toLowerCase().includes("thrissur") ? place : `${place}, Thrissur, Kerala`;
        
        const response = await fetch(
            `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(searchQuery)}`
        );
        const data = await response.json();

        if (!data.length) {
            throw new Error(`Location not found: ${place}`);
        }

        // Validate the location returned is actually within Thrissur
        const displayName = (data[0].display_name || "").toLowerCase();
        if (!displayName.includes("thrissur")) {
            throw new Error("Demo restricted to Thrissur district. Area is outside Thrissur.");
        }

        return {
            lat: parseFloat(data[0].lat),
            lng: parseFloat(data[0].lon)
        };
    } catch (e) {
        console.error("Geocoding error:", e);
        throw e;
    }
}

// -------- AUTHENTICATION STATUS --------
async function checkAuthStatus() {
    try {
        const response = await fetch('/api/user_status');
        const data = await response.json();
        const authLinks = document.getElementById('auth-links');
        
        if (data.logged_in) {
            currentUser = data.username;
            authLinks.innerHTML = `
                <span class="nav-welcome">Hi, ${data.username}!</span>
                <a href="/history" class="nav-link"><i class="fa-solid fa-clock-rotate-left"></i> History</a>
                <a href="#" onclick="logoutUser(event)" class="nav-link"><i class="fa-solid fa-arrow-right-from-bracket"></i> Logout</a>
            `;
        }
    } catch (e) {
        console.error("Auth status fetch failed:", e);
    }
}

window.logoutUser = async function(e) {
    if(e) e.preventDefault();
    try {
        await fetch('/api/logout', { method: 'POST' });
        window.location.reload();
    } catch (err) {
        console.error(err);
    }
}

// -------- AUTOCOMPLETE --------
function setupAutocomplete(inputId, suggestionsId) {
    const input = document.getElementById(inputId);
    const suggestionsBox = document.getElementById(suggestionsId);
    let timeout = null;

    input.addEventListener('input', (e) => {
        clearTimeout(timeout);
        const query = e.target.value.trim();
        
        if (query.length < 2) {
            suggestionsBox.innerHTML = '';
            suggestionsBox.classList.add('hidden');
            return;
        }

        timeout = setTimeout(async () => {
            try {
                // Force context to Thrissur for fetching options
                const searchQuery = query.toLowerCase().includes("thrissur") ? query : `${query}, Thrissur, Kerala`;
                const response = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(searchQuery)}&limit=5`);
                const data = await response.json();
                
                suggestionsBox.innerHTML = '';
                
                // Keep only valid options in Thrissur
                const validPlaces = data.filter(item => (item.display_name || "").toLowerCase().includes("thrissur"));

                if (validPlaces.length === 0) {
                    suggestionsBox.classList.add('hidden');
                    return;
                }

                validPlaces.forEach(place => {
                    // Shorten the display name for UI
                    const nameParts = place.display_name.split(',');
                    const shortName = nameParts.slice(0, Math.min(3, nameParts.length)).join(',').trim();
                    
                    const div = document.createElement('div');
                    div.className = 'suggestion-item';
                    div.innerHTML = `<i class="fa-solid fa-location-dot"></i> <span>${shortName}</span>`;
                    
                    div.addEventListener('click', () => {
                        input.value = shortName;
                        suggestionsBox.classList.add('hidden');
                    });
                    suggestionsBox.appendChild(div);
                });
                suggestionsBox.classList.remove('hidden');
            } catch (err) {
                console.error("Autocomplete fetch error:", err);
            }
        }, 500); // 500ms debounce
    });

    // Hide suggestions when clicking outside
    document.addEventListener('click', (e) => {
        if (e.target !== input && !suggestionsBox.contains(e.target)) {
            suggestionsBox.classList.add('hidden');
        }
    }); // Make sure this bracket closes the setupAutocomplete function nicely
}

// -------- START APP --------
document.addEventListener('DOMContentLoaded', () => {
    initMap();
    checkAuthStatus();
    
    setupAutocomplete('startLocation', 'startSuggestions');
    setupAutocomplete('destination', 'destSuggestions');

    // Select Elements
    const scrollToAnalyzeBtn = document.getElementById('scrollToAnalyze');
    const analyzeSection = document.getElementById('analysis-section');
    const routeForm = document.getElementById('routeForm');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const btnText = analyzeBtn.querySelector('.btn-text');
    const loader = analyzeBtn.querySelector('.loader-spinner');
    const analysisStatus = document.getElementById('analysis-status');

    const riskPanel = document.getElementById('riskPanel');
    const closePanelBtn = document.getElementById('closePanel');

    const riskValueDisplay = document.getElementById('riskValue');
    const riskLevelText = document.getElementById('riskLevelText');
    const warningBox = document.getElementById('warningBox');
    const warningMessage = document.getElementById('warningMessage');
    const accordionContainer = document.querySelector('.accordion');

    // Scroll to Analyze Section
    scrollToAnalyzeBtn.addEventListener('click', () => {
        analyzeSection.scrollIntoView({ behavior: 'smooth' });
    });

    // Close Panel Handler
    closePanelBtn.addEventListener('click', () => {
        riskPanel.classList.remove("active");
    });

    async function getRoute(startCoords, endCoords) {
        try {
            const url = `https://router.project-osrm.org/route/v1/driving/${startCoords.lng},${startCoords.lat};${endCoords.lng},${endCoords.lat}?overview=full&geometries=geojson`;
            const response = await fetch(url);
            const data = await response.json();

            if (!data.routes || !data.routes.length) {
                alert("Route not found.");
                return null;
            }

            return {
                coordinates: data.routes[0].geometry.coordinates,
                distance: data.routes[0].distance
            };
        } catch (e) {
            console.error("Routing error:", e);
            return null;
        }
    }

    function drawRoute(coordinates, segmentRisks) {
        currentRouteCoords = coordinates;

        if (routeLayer) {
            map.removeLayer(routeLayer);
        }
        if (highlightLayer) {
            map.removeLayer(highlightLayer);
        }

        routeLayer = L.featureGroup().addTo(map);
        highlightLayer = L.featureGroup().addTo(map);
        const segmentSize = Math.floor(coordinates.length / segmentRisks.length);

        for (let i = 0; i < segmentRisks.length; i++) {
            const start = i * segmentSize;
            const end = (i === segmentRisks.length - 1) ? coordinates.length : (i + 1) * segmentSize;

            const segmentCoords = coordinates
                .slice(start, end)
                .map(coord => [coord[1], coord[0]]);

            let color = "green";
            if (segmentRisks[i].riskLevel === "High") color = "red";
            else if (segmentRisks[i].riskLevel === "Medium") color = "orange";

            L.polyline(segmentCoords, {
                color: color,
                weight: 7,
                opacity: 0.9
            }).addTo(routeLayer);
        }

        map.fitBounds(routeLayer.getBounds());
    }

    // --- Helper Functions ---
    function setLoading(isLoading, message = "Analyzing...") {
        if (isLoading) {
            analyzeBtn.disabled = true;
            btnText.textContent = "Processing...";
            loader.classList.remove('hidden');
            analysisStatus.textContent = message;
            analysisStatus.classList.remove('hidden');
        } else {
            analyzeBtn.disabled = false;
            btnText.textContent = "Show Risk Analysis";
            loader.classList.add('hidden');
            analysisStatus.classList.add('hidden');
        }
    }

    function clearMap() {
        if (routeLayer) map.removeLayer(routeLayer);
        if (highlightLayer) map.removeLayer(highlightLayer);
        map.eachLayer(function (layer) {
            if (layer instanceof L.Marker) {
                map.removeLayer(layer);
            }
        });
    }

    function highlightSegments(indices) {
        if (highlightLayer) {
            highlightLayer.clearLayers();
        } else {
            highlightLayer = L.featureGroup().addTo(map);
        }

        if (!indices || indices.length === 0 || !currentRouteCoords.length) return;

        // Group indices into continuous paths for better performance
        const segments = [];
        const segmentSize = Math.floor(currentRouteCoords.length / (totalSegmentsCount || 1));

        indices.forEach(idx => {
            const start = idx * segmentSize;
            const end = (idx === totalSegmentsCount - 1) ? currentRouteCoords.length : (idx + 1) * segmentSize;
            const segmentCoords = currentRouteCoords.slice(start, end).map(c => [c[1], c[0]]);

            L.polyline(segmentCoords, {
                color: '#2563EB',
                weight: 12,
                opacity: 0.6,
                lineCap: 'round'
            }).addTo(highlightLayer);
        });

        highlightLayer.bringToFront();
    }

    let totalSegmentsCount = 0;

    function populateRiskPanel(data) {
        totalSegmentsCount = (data.segments || []).length;
        riskValueDisplay.textContent = data.riskScore;
        riskLevelText.textContent = data.riskLevel;
        riskLevelText.style.color = data.riskColor;

        warningMessage.textContent = data.warning;
        warningBox.style.borderColor = data.riskColor;
        warningBox.style.opacity = '0';
        setTimeout(() => {
            warningBox.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            warningBox.style.transform = 'translateY(0)';
            warningBox.style.opacity = '1';
        }, 300);

        accordionContainer.innerHTML = '';
        (data.factors || []).forEach(factor => {
            const item = document.createElement('div');
            item.className = 'accordion-item';
            item.innerHTML = `
                <div class="accordion-header">
                    <span>${factor.name}</span>
                    <span style="color:${factor.color}">${factor.score}/100</span>
                </div>
                <div class="accordion-bar">
                    <div class="accordion-fill" style="width: 0%; background-color: ${factor.color}" data-width="${factor.score}%"></div>
                </div>
                <div class="factor-details">
                    <div class="reason-text">${factor.reason || "Analyzing conditions..."}</div>
                    <div class="tip-box">
                        <span style="font-size: 1.2rem;">💡</span>
                        <span>${factor.tip || "Standard driving precautions apply."}</span>
                    </div>
                </div>
            `;

            item.addEventListener('click', () => {
                // Clear active class from all
                document.querySelectorAll('.accordion-item').forEach(i => i.classList.remove('active-highlight'));

                // Toggle this one
                item.classList.add('active-highlight');
                highlightSegments(factor.riskySegments);
            });

            accordionContainer.appendChild(item);
        });
    }

    function animateRiskCircle(percent, color) {
        const circle = document.getElementById('riskCircle');
        if (!circle) return;
        const radius = circle.r.baseVal.value;
        const circumference = radius * 2 * Math.PI;

        circle.style.strokeDasharray = `${circumference} ${circumference}`;
        circle.style.strokeDashoffset = circumference;
        circle.style.stroke = color;

        const offset = circumference - (percent / 100) * circumference;
        setTimeout(() => {
            circle.style.strokeDashoffset = offset;
        }, 100);
    }

    function animateRiskBars() {
        const bars = document.querySelectorAll('.accordion-fill');
        setTimeout(() => {
            bars.forEach(bar => {
                bar.style.width = bar.getAttribute('data-width');
            });
        }, 200);
    }

    // Form Submission
    routeForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const start = document.getElementById('startLocation').value.trim();
        const dest = document.getElementById('destination').value.trim();
        const frontendError = document.getElementById('frontend-error');
        frontendError.classList.add('hidden');

        if (!start || !dest) {
            frontendError.textContent = "Please enter both a start location and a destination.";
            frontendError.classList.remove('hidden');
            return;
        }

        try {
            setLoading(true, "Locating start and destination...");
            riskPanel.classList.remove('active');
            clearMap();

            const startCoords = await geocodeLocation(start);
            const endCoords = await geocodeLocation(dest);

            setLoading(true, "Generating optimal route path...");
            const routeData = await getRoute(startCoords, endCoords);
            if (!routeData) throw new Error("Could not compute route geometry.");

            const route_segments = buildRouteSegments(routeData.coordinates);

            L.marker([startCoords.lat, startCoords.lng]).addTo(map);
            L.marker([endCoords.lat, endCoords.lng]).addTo(map);
            map.setView([startCoords.lat, startCoords.lng], 10);

            setLoading(true, "Fetching weather & road conditions...");
            const response = await fetch("/analyze_route", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    start_location: start,
                    end_location: dest,
                    segments: route_segments,
                    route_distance: routeData.distance
                })
            });

            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                throw new Error(errData.error || "Server failed to process the route analysis.");
            }

            setLoading(true, "Calculating ML risk scores...");
            const backenddata = await response.json();

            setLoading(true, "Finalizing safety report...");

            drawRoute(routeData.coordinates, backenddata.segments);
            populateRiskPanel(backenddata);

            riskPanel.classList.remove("hidden");
            riskPanel.classList.add("active");

            animateRiskCircle(backenddata.riskScore, backenddata.riskColor);
            animateRiskBars();

        } catch (error) {
            console.error("Analysis failed:", error);
            const frontendError = document.getElementById('frontend-error');
            frontendError.textContent = error.message || "An unexpected error occurred during analysis.";
            frontendError.classList.remove('hidden');
        } finally {
            setLoading(false);
        }
    });

});
