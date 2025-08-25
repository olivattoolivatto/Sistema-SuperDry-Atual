import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix for default markers in leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

const MiniMap = ({ 
  latitude, 
  longitude, 
  title = "Localização",
  className = "",
  height = "150px",
  width = "100%",
  zoom = 15
}) => {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);

  useEffect(() => {
    if (!latitude || !longitude) return;

    // Create map if it doesn't exist
    if (!mapInstanceRef.current && mapRef.current) {
      mapInstanceRef.current = L.map(mapRef.current, {
        zoomControl: false,
        scrollWheelZoom: false,
        doubleClickZoom: false,
        boxZoom: false,
        keyboard: false,
        dragging: false,
        touchZoom: false,
      }).setView([latitude, longitude], zoom);

      // Add OpenStreetMap tiles
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
      }).addTo(mapInstanceRef.current);

      // Add marker
      const marker = L.marker([latitude, longitude]).addTo(mapInstanceRef.current);
      
      if (title && title !== "Localização") {
        marker.bindPopup(title);
      }

      // Add subtle click handler to open in external map
      mapInstanceRef.current.on('click', () => {
        const url = `https://www.google.com/maps?q=${latitude},${longitude}`;
        window.open(url, '_blank');
      });
    }

    // Update map position if coordinates change
    if (mapInstanceRef.current) {
      mapInstanceRef.current.setView([latitude, longitude], zoom);
      
      // Clear existing markers and add new one
      mapInstanceRef.current.eachLayer((layer) => {
        if (layer instanceof L.Marker) {
          mapInstanceRef.current.removeLayer(layer);
        }
      });
      
      const marker = L.marker([latitude, longitude]).addTo(mapInstanceRef.current);
      if (title && title !== "Localização") {
        marker.bindPopup(title);
      }
    }

    return () => {
      // Cleanup on unmount
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, [latitude, longitude, title, zoom]);

  if (!latitude || !longitude) {
    return (
      <div 
        className={`bg-gray-100 rounded-lg flex items-center justify-center ${className}`}
        style={{ height, width }}
      >
        <div className="text-center text-gray-500 text-sm">
          <div className="mb-1">📍</div>
          <div>Sem localização</div>
        </div>
      </div>
    );
  }

  return (
    <div className={`relative ${className}`}>
      <div 
        ref={mapRef}
        style={{ height, width }}
        className="rounded-lg cursor-pointer hover:opacity-90 transition-opacity"
        title="Clique para abrir no Google Maps"
      />
      <div className="absolute top-2 left-2 bg-white bg-opacity-90 px-2 py-1 rounded text-xs font-medium text-gray-700 shadow-sm">
        {title}
      </div>
    </div>
  );
};

export default MiniMap;