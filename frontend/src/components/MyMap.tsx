import 'maplibre-gl/dist/maplibre-gl.css';
import { Feature } from 'geojson';
import { useEffect, useRef, useState } from 'react';
import Map, {
  Layer,
  MapRef,
  NavigationControl,
  ScaleControl,
  Source,
} from 'react-map-gl/maplibre';
import * as turf from '@turf/turf';

import DatasetsControl from './DatasetsControl';
import DrawToolbar from './DrawToolbar';
import ExampleRegions, { Region, regionCoordinates } from './ExampleRegions';

import { mapboxSatelliteBasemapStyle } from './basemapStyles';
import { getBboxGeojson } from './utils';

export type Dataset = {
  id: string;
  bbox: [number, number, number, number];
  epsg: number;
  href: string;
};

export type Datasets = {
  point_cloud: Dataset[];
  raster: Dataset[];
};

export interface FeatureWithId extends Feature {
  id: string;
}

export type Model = 'lidar' | 'both';

export type Result = {
  chm: {
    href: string;
    rescale: string;
    file_size: number;
  };
  ndhm: {
    href: string;
    rescale: string;
    file_size: number;
  };
  building2d: {
    href: string;
    rescale: string;
    file_size: number;
  };
  building3d: {
    href: string;
    rescale: string;
    file_size: number;
  };
  chmv2: {
    href: string;
    rescale: string;
    file_size: number;
  };
  naip?: {
    href: string;
    rescale: string;
    file_size: number;
  };
  session_id: string;
};

export type Task = {
  session_id: string;
  status: string;
  start_time: string;
  end_time?: string;
  payload?: string;
};

export default function MyMap() {
  const [aoi, setAoi] = useState<FeatureWithId | null>(null);
  const [datasets, setDatasets] = useState<Datasets | null>(null);
  const [isPollingProgress, setIsPollingProgress] = useState<boolean>(false);
  const [result, setResult] = useState<Result | null>(null);
  const [selected3dep, setSelected3dep] = useState<Dataset | null>(null);
  const [selectedModel, setSelectedModel] = useState<Model>('lidar');
  const [selectedNaip, setSelectedNaip] = useState<Dataset | null>(null);
  const [viewMode, setViewMode] = useState<
    'chm' | 'ndhm' | 'building2d' | 'building3d' | 'chmv2' | 'naip'
  >('chm');
  const [datasetsIntersection, setDatasetsIntersection] =
    useState<Feature | null>(null);
  const [selectedRegion, setSelectedRegion] = useState<Region>('demopolis');

  const mapRef = useRef<MapRef | null>(null);

  // Handle region selection
  const handleRegionSelect = (region: Region) => {
    setSelectedRegion(region);
    if (mapRef.current) {
      const map = mapRef.current.getMap();
      const [longitude, latitude] = regionCoordinates[region];
      map.flyTo({
        center: [longitude, latitude],
        zoom: 14,
        duration: 1000,
      });
    }
  };

  // Zoom to drawn area of interest (AOI) on its creation
  useEffect(() => {
    if (mapRef.current && aoi) {
      const map = mapRef.current.getMap();
      const bbox = turf.bbox(aoi);

      if (bbox.length === 4) {
        map.fitBounds(bbox, {
          padding: 20,
          duration: 1000,
        });
      }
    }
  }, [aoi]);

  // Zoom to extent of area of interest (AOI) when results are returned
  useEffect(() => {
    if (mapRef.current && aoi && result) {
      const map = mapRef.current.getMap();
      const bbox = turf.bbox(aoi);

      if (bbox.length === 4) {
        map.fitBounds(bbox, {
          padding: 20,
          duration: 1000,
        });
      }
    }
  }, [result]);

  // Pan and zoom map to starting conditions when results are cleared
  useEffect(() => {
    if (mapRef.current && !result) {
      const map = mapRef.current.getMap();
      const [longitude, latitude] = regionCoordinates[selectedRegion];
      map.flyTo({
        center: [longitude, latitude],
        zoom: 14,
        duration: 1000,
      });
    }
  }, [result, selectedRegion]);

  // Zoom to the intersection of selected datasets
  useEffect(() => {
    if (aoi && selected3dep && !selectedNaip) {
      const polygon1 = turf.bboxPolygon(selected3dep.bbox);
      const polygon2 = turf.bboxPolygon(turf.bbox(aoi));
      const intersection = turf.intersect(
        turf.featureCollection([polygon1, polygon2]),
      );
      setDatasetsIntersection(intersection);
      if (mapRef.current) {
        const map = mapRef.current.getMap();
        if (intersection) {
          const bbox = turf.bbox(intersection);
          if (bbox.length === 4) {
            map.fitBounds(bbox, {
              padding: 20,
              duration: 1000,
            });
          }
        }
      }
    } else if (aoi && selected3dep && selectedNaip) {
      const polygon1 = turf.bboxPolygon(selected3dep.bbox);
      const polygon2 = turf.bboxPolygon(selectedNaip.bbox);
      const polygon3 = turf.bboxPolygon(turf.bbox(aoi));
      const intersection = turf.intersect(
        turf.featureCollection([polygon1, polygon2, polygon3]),
      );
      setDatasetsIntersection(intersection);
      if (mapRef.current) {
        const map = mapRef.current.getMap();
        if (intersection) {
          const bbox = turf.bbox(intersection);
          if (bbox.length === 4) {
            map.fitBounds(bbox, {
              padding: 20,
              duration: 1000,
            });
          }
        }
      }
    } else if (aoi && selectedNaip && !selected3dep) {
      const polygon1 = turf.bboxPolygon(selectedNaip.bbox);
      const polygon2 = turf.bboxPolygon(turf.bbox(aoi));
      const intersection = turf.intersect(
        turf.featureCollection([polygon1, polygon2]),
      );
      setDatasetsIntersection(intersection);
      if (mapRef.current) {
        const map = mapRef.current.getMap();
        if (intersection) {
          const bbox = turf.bbox(intersection);
          if (bbox.length === 4) {
            map.fitBounds(bbox, {
              padding: 20,
              duration: 1000,
            });
          }
        }
      }
    }
  }, [selected3dep, selectedNaip]);

  return (
    <Map
      ref={mapRef}
      initialViewState={{
        longitude: regionCoordinates[selectedRegion][0],
        latitude: regionCoordinates[selectedRegion][1],
        zoom: 14,
      }}
      style={{ width: '100%', height: '100%' }}
      mapStyle={mapboxSatelliteBasemapStyle}
    >
      <ExampleRegions onRegionSelect={handleRegionSelect} />
      {aoi && datasets && (
        <DatasetsControl
          aoi={aoi}
          datasets={datasets}
          result={result}
          isPollingProgress={isPollingProgress}
          setAoi={setAoi}
          setDatasets={setDatasets}
          setDatasetIntersection={setDatasetsIntersection}
          selected3DEP={selected3dep}
          selectedModel={selectedModel}
          selectedNaip={selectedNaip}
          setIsPollingProgress={setIsPollingProgress}
          setSelected3DEP={setSelected3dep}
          setSelectedModel={setSelectedModel}
          setSelectedNaip={setSelectedNaip}
          setResult={setResult}
          setViewMode={setViewMode}
          viewMode={viewMode}
        />
      )}
      {aoi && !result && (
        <Source
          id="bbox-aoi-source"
          type="geojson"
          data={turf.bboxPolygon(turf.bbox(aoi))}
        >
          <Layer
            id="bbox-aoi-layer"
            type="fill"
            paint={{ 'fill-color': '#fde68a', 'fill-opacity': 0.6 }}
          />
          <Layer
            id="bbox-aoi-border"
            type="line"
            paint={{ 'line-color': '#f59e0b', 'line-width': 2 }}
          />
        </Source>
      )}
      {selected3dep && !datasetsIntersection && !result && (
        <Source
          id="bbox-3dep-source"
          type="geojson"
          data={getBboxGeojson(selected3dep.bbox)}
        >
          <Layer
            id="bbox-3dep-layer"
            type="fill"
            paint={{ 'fill-color': '#888888', 'fill-opacity': 0.5 }}
          />
          <Layer
            id="bbox-3dep-border"
            type="line"
            paint={{
              'line-color': '#000000',
              'line-width': 2,
            }}
          />
        </Source>
      )}
      {selectedNaip && !datasetsIntersection && !result && (
        <Source
          id="bbox-naip-source"
          type="geojson"
          data={getBboxGeojson(selectedNaip.bbox)}
        >
          <Layer
            id="bbox-naip-layer"
            type="fill"
            paint={{ 'fill-color': '#a3e635', 'fill-opacity': 0.5 }}
          />
          <Layer
            id="bbox-naip-border"
            type="line"
            paint={{
              'line-color': '#000000',
              'line-width': 2,
            }}
          />
        </Source>
      )}
      {datasetsIntersection && !result && (
        <Source
          id="bbox-intersection-source"
          type="geojson"
          data={datasetsIntersection}
        >
          <Layer
            id="bbox-intersection-layer"
            type="fill"
            paint={{ 'fill-color': '#84cc16', 'fill-opacity': 0.6 }}
          />
          <Layer
            id="bbox-intersection-border"
            type="line"
            paint={{
              'line-color': '#3f6212',
              'line-width': 2,
              'line-dasharray': [4, 2],
            }}
          />
        </Source>
      )}
      {aoi && result && result?.[viewMode] && (
        <Source
          key={viewMode}
          id={`${viewMode}-source`}
          type="raster"
          tiles={[
            '/cog/tiles/WebMercatorQuad/{z}/{x}/{y}@2x?url=' +
              `${result[viewMode].href}&${result[viewMode].rescale}` +
              `${viewMode !== 'naip' ? '&colormap_name=jet&nodata=255' : ''}`,
          ]}
          maxzoom={24}
          minzoom={0}
          tileSize={512}
          bounds={turf.bbox(aoi) as [number, number, number, number]}
        >
          <Layer
            id={`${viewMode}-layer`}
            type="raster"
            source={result.session_id}
          />
        </Source>
      )}
      <DrawToolbar
        aoi={aoi}
        result={result}
        setAoi={setAoi}
        setDatasets={setDatasets}
      />
      <ScaleControl />
      <NavigationControl />
    </Map>
  );
}
