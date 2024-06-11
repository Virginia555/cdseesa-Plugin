 // Inizializza la mappa
 var map = L.map('map').setView([42.5, 12.5], 6); // Centro iniziale della mappa Italy

 // Aggiungi un layer della mappa di OpenStreetMap
 L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
     attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
 }).addTo(map);

 // Funzione per ottenere le coordinate dalla città e dal paese utilizzando OpenStreetMap Nominatim
 function getCoordinates(city, callback) {
     $.getJSON('https://nominatim.openstreetmap.org/search?format=json&q=' + city, function(data) {
         if (data.length > 0) {
             var lat = data[0].lat;
             var lon = data[0].lon;
             callback(lat, lon);
         }
     });
 }

 var locationResults = {};

 function addOrUpdateMarker(location, lat, lon, content) {
     if (locationResults[location]) {
         // Update popup content and refresh the popup
         locationResults[location].popupContent += '<br><br>' + content;
         locationResults[location].marker.bindPopup(locationResults[location].popupContent);
     } else {
         // Create new marker and bind initial popup content
         var marker = L.marker([lat, lon]).addTo(map);
         marker.bindPopup(content);
         locationResults[location] = {
             marker: marker,
             popupContent: '<h1><b>'+ location + '</b></h1><br>' + content
         };
     }
 }

 // Iterate over results to populate the markers
 {% for result in results|reverse %}
     getCoordinates("{{ result.Location }}", function(lat, lon) {
         var content = "<b>{{ result.Date }}<br>Avg Response Time</b> = {{ result.avgResponseTime }}<br><b>Peak Response Time</b> = {{results.peakResponseTime}}<br><b>Error Rate</b> = {{results.errorRate}}<br><b>Avg Concurrency</b> = {{result.avgConcurrency}}<br><b>Peak Concurrency</b> = {{result.peakConcurrency}}";
         addOrUpdateMarker('{{ result.Location }}', lat, lon, content);
     });
 {% endfor %}

