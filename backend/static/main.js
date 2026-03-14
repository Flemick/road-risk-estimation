let map;
let routeLayer;
let highlightLayer;
let currentRouteCoords = [];

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
        const response = await fetch(
            `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(place)}`
        );
        const data = await response.json();

        if (!data.length) {
            alert("Location not found: " + place);
            return null;
        }

        return {
            lat: parseFloat(data[0].lat),
            lng: parseFloat(data[0].lon)
        };
    } catch (e) {
        console.error("Geocoding error:", e);
        return null;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    initMap();

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

        const start = document.getElementById('startLocation').value;
        const dest = document.getElementById('destination').value;
        if (!start || !dest) return;

        try {
            setLoading(true, "Locating start and destination...");
            riskPanel.classList.remove('active');
            clearMap();

            const startCoords = await geocodeLocation(start);
            const endCoords = await geocodeLocation(dest);
            if (!startCoords || !endCoords) { setLoading(false); return; }

            setLoading(true, "Generating optimal route path...");
            const routeData = await getRoute(startCoords, endCoords);
            if (!routeData) { setLoading(false); return; }

            const route_segments = buildRouteSegments(routeData.coordinates);

            L.marker([startCoords.lat, startCoords.lng]).addTo(map);
            L.marker([endCoords.lat, endCoords.lng]).addTo(map);
            map.setView([startCoords.lat, startCoords.lng], 10);

            setLoading(true, "Fetching weather & road conditions...");
            const response = await fetch("/analyze_route", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    start: start,
                    destination: dest,
                    segments: route_segments,
                    route_distance: routeData.distance
                })
            });

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
            console.error("Analysis failed", error);
            alert("An error occurred during analysis.");
        } finally {
            setLoading(false);
        }
    });

});
