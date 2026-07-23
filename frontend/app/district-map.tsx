"use client";

import { useEffect, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import { type Map as MapLibreMap, type Marker } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

import type { DistrictStatus } from "./mock-data";

const DISTRICTS = [
  { name: "Tay Ho", latitude: 21.070, longitude: 105.818 },
  { name: "Long Bien", latitude: 21.045, longitude: 105.892 },
  { name: "Ba Dinh", latitude: 21.035, longitude: 105.815 },
  { name: "Cau Giay", latitude: 21.035, longitude: 105.793 },
  { name: "Hoan Kiem", latitude: 21.028, longitude: 105.854 },
  { name: "Dong Da", latitude: 21.018, longitude: 105.830 },
  { name: "Hai Ba Trung", latitude: 21.005, longitude: 105.855 },
  { name: "Thanh Xuan", latitude: 20.995, longitude: 105.813 },
];

type DistrictMapProps = {
  districts: DistrictStatus[];
  selectedDistrictName: string;
  onSelect: (districtName: string) => void;
};

export default function DistrictMap({
  districts,
  selectedDistrictName,
  onSelect,
}: DistrictMapProps) {
  const mapContainer = useRef<HTMLDivElement | null>(null);
  const map = useRef<MapLibreMap | null>(null);
  const markers = useRef<Marker[]>([]);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    map.current = new maplibregl.Map({
      container: mapContainer.current,
      center: [105.837, 21.031],
      // Starting one level farther out means the browser needs fewer map tiles
      // before the useful Hanoi view is visible.
      zoom: 10.6,
      minZoom: 10,
      maxZoom: 15,
      fadeDuration: 0,
      refreshExpiredTiles: false,
      renderWorldCopies: false,
      style: {
        version: 8,
        sources: {
          cartoLight: {
            type: "raster",
            tiles: ["https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"],
            tileSize: 256,
            attribution: "© OpenStreetMap contributors © CARTO",
          },
        },
        layers: [{ id: "carto-light", type: "raster", source: "cartoLight" }],
      },
    });
    map.current.addControl(new maplibregl.NavigationControl(), "top-right");
    // The style is ready before every raster tile has downloaded.  Removing the
    // loading message at this point lets people start using the map immediately.
    map.current.once("style.load", () => setIsReady(true));

    return () => {
      map.current?.remove();
      map.current = null;
    };
  }, []);

  useEffect(() => {
    if (!map.current) return;

    markers.current.forEach((marker) => marker.remove());
    markers.current = DISTRICTS.filter((district) =>
      districts.some((item) => item.district_name === district.name),
    ).map((district) => {
      const status = districts.find((item) => item.district_name === district.name);
      const element = document.createElement("button");
      element.type = "button";
      element.className = `map-district-marker${
        district.name === selectedDistrictName ? " selected" : ""
      }`;
      element.setAttribute("aria-label", `Show ${district.name} district status`);
      element.innerHTML = `<strong>${status?.us_aqi ?? "–"}</strong><span>${district.name}</span>`;
      element.addEventListener("click", () => onSelect(district.name));

      return new maplibregl.Marker({ element, anchor: "center" })
        .setLngLat([district.longitude, district.latitude])
        .addTo(map.current!);
    });
  }, [districts, onSelect, selectedDistrictName]);

  return (
    <div className="district-map-shell">
      <div className="district-map" ref={mapContainer} />
      {!isReady && <div className="district-map-loading">Loading live map…</div>}
    </div>
  );
}
