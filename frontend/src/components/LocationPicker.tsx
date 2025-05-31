import React, { useEffect, useRef, useState } from 'react';

interface LocationPickerProps {
  onLocationSelect: (address: string) => void;
}

declare global {
  interface Window {
    google: any;
    initMap: () => void;
  }
}

const LocationPicker: React.FC<LocationPickerProps> = ({ onLocationSelect }) => {
  const mapRef = useRef<HTMLDivElement>(null);
  const [map, setMap] = useState<any>(null);
  const [marker, setMarker] = useState<any>(null);
  const [geocoder, setGeocoder] = useState<any>(null);

  useEffect(() => {
    // Load Google Maps script
    const script = document.createElement('script');
    script.src = `https://maps.googleapis.com/maps/api/js?key=AIzaSyAB_RNeA3SUG_mUivMEZrKECowFebeHChw&callback=initMap`;
    script.async = true;
    script.defer = true;
    document.head.appendChild(script);

    window.initMap = () => {
      if (mapRef.current) {
        const initialMap = new window.google.maps.Map(mapRef.current, {
          center: { lat: -23.550520, lng: -46.633308 }, // São Paulo coordinates
          zoom: 12,
          mapTypeControl: true,
          streetViewControl: true,
          fullscreenControl: true,
        });

        const initialGeocoder = new window.google.maps.Geocoder();
        setMap(initialMap);
        setGeocoder(initialGeocoder);

        // Add click listener to map
        initialMap.addListener('click', (e: any) => {
          const lat = e.latLng.lat();
          const lng = e.latLng.lng();

          // Remove existing marker if any
          if (marker) {
            marker.setMap(null);
          }

          // Add new marker
          const newMarker = new window.google.maps.Marker({
            position: { lat, lng },
            map: initialMap,
            animation: window.google.maps.Animation.DROP
          });
          setMarker(newMarker);

          // Get address from coordinates
          initialGeocoder.geocode({ location: { lat, lng } }, (results: any, status: string) => {
            if (status === 'OK' && results[0]) {
              onLocationSelect(results[0].formatted_address);
            }
          });
        });
      }
    };

    return () => {
      // Cleanup
      document.head.removeChild(script);
      delete window.initMap;
    };
  }, [onLocationSelect]);

  return (
    <div className="w-full h-[400px] rounded-lg overflow-hidden shadow-lg">
      <div ref={mapRef} className="w-full h-full" />
    </div>
  );
};

export default LocationPicker; 