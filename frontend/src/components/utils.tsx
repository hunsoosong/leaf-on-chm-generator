import { FeatureCollection } from 'geojson';

const getBboxGeojson = (
  bbox: [number, number, number, number]
): FeatureCollection => ({
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      geometry: {
        type: 'Polygon',
        coordinates: [
          [
            [bbox[0], bbox[1]],
            [bbox[2], bbox[1]],
            [bbox[2], bbox[3]],
            [bbox[0], bbox[3]],
            [bbox[0], bbox[1]],
          ],
        ],
      },
      properties: {},
    },
  ],
});

export { getBboxGeojson };
