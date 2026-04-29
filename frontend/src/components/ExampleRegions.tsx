import { FC } from 'react';

export type Region = 'demopolis' | 'manhattan' | 'purdue';

export const regionCoordinates: Record<Region, [number, number]> = {
  demopolis: [-87.8375, 32.5176], // Demopolis, AL coordinates
  manhattan: [-96.5717, 39.1836], // Manhattan, KS coordinates
  purdue: [-78.1944, 38.9182], // Front Royal, VA coordinates
};

interface ExampleRegionsProps {
  onRegionSelect: (region: Region) => void;
}

const ExampleRegions: FC<ExampleRegionsProps> = ({ onRegionSelect }) => {
  return (
    <div
      style={{
        position: 'absolute',
        top: '10px',
        left: '50%',
        transform: 'translateX(-50%)',
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        padding: '12px 16px',
        borderRadius: '6px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
        zIndex: 1,
        color: 'black',
        fontFamily: 'Arial, sans-serif',
        width: '360px',
        maxWidth: '360px',
      }}
    >
      <div
        style={{
          marginBottom: '8px',
          fontWeight: 'bold',
          color: 'black',
          fontSize: '16px',
          textTransform: 'uppercase',
          letterSpacing: '0.5px',
        }}
      >
        Example Areas
      </div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          color: 'black',
          fontSize: '13px',
          marginBottom: '12px',
          gap: '8px',
        }}
      >
        <label
          style={{
            color: 'black',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            cursor: 'pointer',
            whiteSpace: 'nowrap',
          }}
        >
          <input
            type="radio"
            name="region"
            value="demopolis"
            defaultChecked
            onChange={(e) => onRegionSelect(e.target.value as Region)}
            style={{ cursor: 'pointer' }}
          />
          Demopolis, AL
        </label>
        <label
          style={{
            color: 'black',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            cursor: 'pointer',
            whiteSpace: 'nowrap',
          }}
        >
          <input
            type="radio"
            name="region"
            value="manhattan"
            onChange={(e) => onRegionSelect(e.target.value as Region)}
            style={{ cursor: 'pointer' }}
          />
          Manhattan, KS
        </label>
        <label
          style={{
            color: 'black',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            cursor: 'pointer',
            whiteSpace: 'nowrap',
          }}
        >
          <input
            type="radio"
            name="region"
            value="purdue"
            onChange={(e) => onRegionSelect(e.target.value as Region)}
            style={{ cursor: 'pointer' }}
          />
          Front Royal, VA
        </label>
      </div>
      <div
        style={{
          fontSize: '13px',
          color: '#333',
          borderTop: '1px solid #ddd',
          paddingTop: '12px',
          lineHeight: '1.4',
        }}
      >
        <p style={{ margin: '0 0 8px 0' }}>
          <strong>Getting Started:</strong> Use the drawing toolbar on the left
          to draw a polygon around your area of interest. The map will
          automatically zoom to your selection.
        </p>
      </div>
    </div>
  );
};

export default ExampleRegions;
