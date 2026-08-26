import { useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Circle, Polyline, useMap } from 'react-leaflet';
import L from 'leaflet';
import type { Location, MapData } from '../types';

interface MarineMapProps {
  mapData: MapData | null;
  onMapClick: (lat: number, lng: number) => void;
  selectedLocation: Location | null;
}

// Fix Leaflet default icon issue
delete (L.Icon.Default.prototype as Record<string, unknown>)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

function createEmojiIcon(emoji: string, size: number = 30) {
  return L.divIcon({
    html: `<div style="font-size:${size}px;line-height:1;filter:drop-shadow(0 2px 4px rgba(0,0,0,0.5))">${emoji}</div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    className: '',
  });
}

function MapUpdater({ center, zoom }: { center: [number, number]; zoom: number }) {
  const map = useMap();
  useEffect(() => {
    map.flyTo(center, zoom, { duration: 1.5 });
  }, [center, zoom, map]);
  return null;
}

function ClickHandler({ onClick }: { onClick: (lat: number, lng: number) => void }) {
  const map = useMap();
  useEffect(() => {
    const handler = (e: L.LeafletMouseEvent) => {
      onClick(e.latlng.lat, e.latlng.lng);
    };
    map.on('click', handler);
    return () => { map.off('click', handler); };
  }, [map, onClick]);
  return null;
}

const RISK_COLORS: Record<string, string> = {
  safe: '#2ecc71',
  caution: '#f1c40f',
  high_risk: '#e67e22',
  extreme_risk: '#e74c3c',
};

export function MarineMap({ mapData, onMapClick, selectedLocation }: MarineMapProps) {
  const center = useMemo<[number, number]>(() => {
    if (mapData?.center) return [mapData.center.lat, mapData.center.lng];
    if (selectedLocation) return [selectedLocation.lat, selectedLocation.lng];
    return [20.0, 85.0]; // Default: Bay of Bengal
  }, [mapData, selectedLocation]);

  const zoom = mapData?.zoom || 7;

  return (
    <MapContainer
      center={center}
      zoom={zoom}
      className="w-full h-full"
      zoomControl={true}
    >
      <TileLayer
        attribution='Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ'
        url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}"
      />

      <MapUpdater center={center} zoom={zoom} />
      <ClickHandler onClick={onMapClick} />

      {/* Selected Location */}
      {selectedLocation && (
        <Marker
          position={[selectedLocation.lat, selectedLocation.lng]}
          icon={createEmojiIcon('📍', 32)}
        >
          <Popup>
            <div className="text-sm">
              <strong>📍 {selectedLocation.name || 'Selected Location'}</strong><br />
              {selectedLocation.lat.toFixed(4)}°N, {selectedLocation.lng.toFixed(4)}°E
            </div>
          </Popup>
        </Marker>
      )}

      {/* Map markers from response */}
      {mapData?.markers.map((marker, i) => (
        <Marker
          key={`marker-${i}`}
          position={[marker.lat, marker.lng]}
          icon={createEmojiIcon(marker.icon, marker.type === 'user_location' ? 32 : 28)}
        >
          <Popup>
            <div className="text-sm min-w-[150px]">
              <strong>{marker.icon} {marker.label}</strong>
              {marker.distance != null && (
                <div>Distance: {marker.distance} km</div>
              )}
              {marker.sst != null && (
                <div>SST: {marker.sst}°C</div>
              )}
              {marker.score != null && (
                <div>Score: {marker.score}/100</div>
              )}
            </div>
          </Popup>
        </Marker>
      ))}

      {/* Risk zones */}
      {mapData?.zones.map((zone, i) => (
        <Circle
          key={`zone-${i}`}
          center={[zone.center_lat, zone.center_lng]}
          radius={zone.radius_km * 1000}
          pathOptions={{
            color: RISK_COLORS[zone.risk_level] || '#f1c40f',
            fillColor: RISK_COLORS[zone.risk_level] || '#f1c40f',
            fillOpacity: 0.08,
            weight: 2,
            dashArray: '8 4',
          }}
        />
      ))}

      {/* Routes */}
      {mapData?.routes.map((route, i) => (
        <Polyline
          key={`route-${i}`}
          positions={route.waypoints.map(wp => [wp.lat, wp.lng] as [number, number])}
          pathOptions={{
            color: route.color,
            weight: route.recommended ? 4 : 2,
            opacity: route.recommended ? 0.9 : 0.4,
            dashArray: route.recommended ? undefined : '10 6',
          }}
        />
      ))}
    </MapContainer>
  );
}
