"use client";

// Real interactive map via MapLibre GL JS with free raster tiles.
// Light: OpenStreetMap. Dark: CARTO Dark Matter (OSM-derived).
// No API key required. Attribution is always displayed.

import React from "react";
import {
  AttributionControl,
  LngLatBounds,
  Map as MapLibreMap,
  Marker,
  NavigationControl,
  setWorkerUrl,
  type StyleSpecification,
} from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { MapPlace } from "./presence-sphere";

const OSM_ATTR =
  '© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors';

const LIGHT_STYLE: StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: OSM_ATTR,
    },
  },
  layers: [{ id: "osm", type: "raster", source: "osm" }],
};

const DARK_STYLE: StyleSpecification = {
  version: 8,
  sources: {
    carto: {
      type: "raster",
      tiles: ["https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: `${OSM_ATTR} © <a href="https://carto.com/attributions" target="_blank" rel="noopener noreferrer">CARTO</a>`,
    },
  },
  layers: [{ id: "carto", type: "raster", source: "carto" }],
};

export interface GeoMapProps {
  places: MapPlace[];
  dark?: boolean;
  onSelect?: (place: MapPlace) => void;
}

export default function GeoMap({ places, dark = false, onSelect }: GeoMapProps) {
  const containerRef = React.useRef<HTMLDivElement>(null);
  const mapRef = React.useRef<MapLibreMap | null>(null);
  const markersRef = React.useRef<Marker[]>([]);
  const selectRef = React.useRef(onSelect);
  selectRef.current = onSelect;

  React.useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    // Next.js cannot reliably resolve MapLibre's bundled worker chunk. Serve a
    // stable, self-contained copy from /public so the tile worker actually runs.
    setWorkerUrl("/maplibre-worker.mjs");
    const map = new MapLibreMap({
      container: containerRef.current,
      style: dark ? DARK_STYLE : LIGHT_STYLE,
      center: [18.4, -30.5], // IAM's operational home (South Africa)
      zoom: 3,
      attributionControl: false,
      cooperativeGestures: false,
    });
    mapRef.current = map;
    map.addControl(new AttributionControl({ compact: true }), "bottom-right");
    map.addControl(new NavigationControl({ showCompass: false }), "top-right");

    const onResize = () => map.resize();
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      markersRef.current.forEach((m) => m.remove());
      markersRef.current = [];
      map.remove();
      mapRef.current = null;
    };
    // Mount once; theme changes are handled by the effect below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  React.useEffect(() => {
    mapRef.current?.setStyle(dark ? DARK_STYLE : LIGHT_STYLE);
  }, [dark]);

  React.useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    markersRef.current.forEach((m) => m.remove());
    markersRef.current = [];
    const bounds = new LngLatBounds();
    for (const place of places) {
      if (!Number.isFinite(place.latitude) || !Number.isFinite(place.longitude)) continue;
      const el = document.createElement("button");
      el.type = "button";
      el.title = place.name;
      el.setAttribute("aria-label", `Inspect ${place.name}`);
      el.style.cssText = [
        "width:14px", "height:14px", "border-radius:50%",
        "border:2px solid rgba(255,255,255,.9)",
        "background:hsl(265 85% 62%)",
        "boxShadow:0 0 0 3px rgba(139,92,246,.28),0 2px 8px rgba(0,0,0,.45)",
        "cursor:pointer", "padding:0",
      ].join(";");
      el.addEventListener("click", () => selectRef.current?.(place));
      const marker = new Marker({ element: el })
        .setLngLat([place.longitude, place.latitude])
        .addTo(map);
      markersRef.current.push(marker);
      bounds.extend([place.longitude, place.latitude]);
    }
    if (!bounds.isEmpty()) {
      map.fitBounds(bounds, { padding: 90, maxZoom: 7, duration: 700 });
    }
  }, [places]);

  return (
    <div
      ref={containerRef}
      className="absolute inset-0 h-full w-full"
      aria-label="Interactive geospatial map of IAM knowledge locations"
    />
  );
}
