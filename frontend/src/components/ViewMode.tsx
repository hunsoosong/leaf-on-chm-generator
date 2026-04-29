import './ViewMode.css';

import { Result } from './MyMap';

export default function ViewMode({
  result,
  setViewMode,
  viewMode,
}: {
  result: Result | null;
  setViewMode: React.Dispatch<
    React.SetStateAction<
      'chm' | 'ndhm' | 'building2d' | 'building3d' | 'chmv2' | 'naip'
    >
  >;
  viewMode: 'chm' | 'ndhm' | 'building2d' | 'building3d' | 'chmv2' | 'naip';
}) {
  if (!result || !result?.chm || !result?.ndhm) return;

  return (
    <div className="view-mode">
      <fieldset>
        <legend>Results</legend>
        <h3>Display on map</h3>
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
          }}
        >
          <div>
            <input
              type="radio"
              id="chm"
              name="viewMode"
              value="chm"
              checked={viewMode === 'chm'}
              onChange={(e) => setViewMode(e.target.value as 'chm')}
            />
            <label htmlFor="chm">Generated CHM</label>
          </div>
          <div>
            <input
              type="radio"
              id="ndhm"
              name="viewMode"
              value="ndhm"
              checked={viewMode === 'ndhm'}
              onChange={(e) => setViewMode(e.target.value as 'ndhm')}
            />
            <label htmlFor="ndhm">NDHM</label>
          </div>
          <div>
            <input
              type="radio"
              id="building2d"
              name="viewMode"
              value="building2d"
              checked={viewMode === 'building2d'}
              onChange={(e) => setViewMode(e.target.value as 'building2d')}
            />
            <label htmlFor="building2d">2D Building</label>
          </div>
          <div>
            <input
              type="radio"
              id="building3d"
              name="viewMode"
              value="building3d"
              checked={viewMode === 'building3d'}
              onChange={(e) => setViewMode(e.target.value as 'building3d')}
            />
            <label htmlFor="building3d">3D Building</label>
          </div>
          <div>
            <input
              type="radio"
              id="chmv2"
              name="viewMode"
              value="chmv2"
              checked={viewMode === 'chmv2'}
              onChange={(e) => setViewMode(e.target.value as 'chmv2')}
            />
            <label htmlFor="chmv2">Generated CHM v2</label>
          </div>
          {result?.naip && (
            <div>
              <input
                type="radio"
                id="naip"
                name="viewMode"
                value="naip"
                checked={viewMode === 'naip'}
                onChange={(e) => setViewMode(e.target.value as 'naip')}
              />
              <label htmlFor="naip">NAIP</label>
            </div>
          )}
        </div>

        <h3>Download</h3>
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
          }}
        >
          <a
            href={result.chm.href}
            download="generated-chm.tif"
            aria-label="Download Generated CHM file"
            type="image/tiff"
          >
            {`Generated CHM (GeoTIFF, ${(
              result.chm.file_size /
              (1024 * 1024)
            ).toFixed(2)} MB)`}
          </a>
          <a
            href={result.ndhm.href}
            download="ndhm.tif"
            aria-label="Download NDHM file"
            type="image/tiff"
          >
            {`NDHM (GeoTIFF, ${(result.ndhm.file_size / (1024 * 1024)).toFixed(
              2
            )} MB)`}
          </a>
          <a
            href={result.building2d.href}
            download="building2d.tif"
            aria-label="Download 2D building file"
            type="image/tiff"
          >
            {`2D Building (GeoTIFF, ${(
              result.building2d.file_size /
              (1024 * 1024)
            ).toFixed(2)} MB)`}
          </a>
          <a
            href={result.building3d.href}
            download="building3d.tif"
            aria-label="Download 3D building file"
            type="image/tiff"
          >
            {`3D Building (GeoTIFF, ${(
              result.building3d.file_size /
              (1024 * 1024)
            ).toFixed(2)} MB)`}
          </a>
          <a
            href={result.chmv2.href}
            download="chmv2.tif"
            aria-label="Download Generated CHM v2 file"
            type="image/tiff"
          >
            {`Generated CHM v2 (GeoTIFF, ${(
              result.chmv2.file_size /
              (1024 * 1024)
            ).toFixed(2)} MB)`}
          </a>
          {result.naip && (
            <a
              href={result.naip.href}
              download="naip.tif"
              aria-label="Download NAIP file"
              type="image/tiff"
            >
              {`NAIP (GeoTIFF, ${(
                result.naip.file_size /
                (1024 * 1024)
              ).toFixed(2)} MB)`}
            </a>
          )}
        </div>
      </fieldset>
    </div>
  );
}
