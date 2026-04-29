import './DatasetsControl.css';
import { Feature, Geometry, GeoJsonProperties } from 'geojson';
import { useEffect, useState } from 'react';
import { area } from '@turf/area';

import { Dataset, Datasets, FeatureWithId, Model, Result, Task } from './MyMap';
import ViewMode from './ViewMode';

type DatasetsControlProps = {
  aoi: Feature;
  datasets: Datasets;
  isPollingProgress: boolean;
  result: Result | null;
  setAoi: React.Dispatch<React.SetStateAction<FeatureWithId | null>>;
  setDatasets: React.Dispatch<React.SetStateAction<Datasets | null>>;
  selected3DEP: Dataset | null;
  selectedModel: Model;
  selectedNaip: Dataset | null;
  setDatasetIntersection: React.Dispatch<
    React.SetStateAction<Feature<Geometry, GeoJsonProperties> | null>
  >;
  setIsPollingProgress: React.Dispatch<React.SetStateAction<boolean>>;
  setSelected3DEP: React.Dispatch<React.SetStateAction<Dataset | null>>;
  setSelectedModel: React.Dispatch<React.SetStateAction<Model>>;
  setSelectedNaip: React.Dispatch<React.SetStateAction<Dataset | null>>;
  setResult: React.Dispatch<React.SetStateAction<Result | null>>;
  viewMode: 'chm' | 'ndhm' | 'building2d' | 'building3d' | 'chmv2' | 'naip';
  setViewMode: React.Dispatch<
    React.SetStateAction<
      'ndhm' | 'chm' | 'building2d' | 'building3d' | 'chmv2' | 'naip'
    >
  >;
};

export default function DatasetsControl({
  aoi,
  datasets,
  isPollingProgress,
  result,
  setAoi,
  setDatasets,
  selected3DEP,
  selectedModel,
  selectedNaip,
  setDatasetIntersection,
  setIsPollingProgress,
  setSelected3DEP,
  setSelectedModel,
  setSelectedNaip,
  setResult,
  viewMode,
  setViewMode,
}: DatasetsControlProps) {
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const areaLimit = Number(import.meta.env?.VITE_AOI_AREA_LIMIT) || 1000000;
    if (aoi && area(aoi) > areaLimit) {
      setError(
        `The selected area is too large. It measures ${parseFloat(
          area(aoi).toFixed(2)
        ).toLocaleString()} square meters, but must be less than ${areaLimit.toLocaleString()} square meters. Please reset and draw a smaller area.`
      );
    }
  }, [aoi]);

  const handleReset = () => {
    setError('');
    setIsPollingProgress(false);
    setResult(null);
    setSelected3DEP(null);
    setSelectedNaip(null);
    setDatasets(null);
    setViewMode('chm');
    setDatasetIntersection(null);
    setAoi(null);
  };

  const checkStatus = async (sessionId: string) => {
    try {
      const response = await fetch(`/api/check_status?session_id=${sessionId}`);
      const data: Task = await response.json();
      if (data.status === 'finished') {
        if (data.payload) {
          const result = JSON.parse(data.payload) as Result;
          setResult(result);
          setIsPollingProgress(false);
        }
      } else if (data.status === 'pending' || data.status === 'running') {
        setTimeout(() => {
          checkStatus(sessionId);
        }, 5000);
      } else if (data.status === 'error') {
        console.error('Error: Unable to process request.');
        setError('Error: Unable to process request.');
        setIsPollingProgress(false);
      } else {
        console.error('Error: Unable to process request.');
        setError('Error: Unable to process request.');
        setIsPollingProgress(false);
      }
    } catch (err) {
      console.error('Error:', err);
      setError('Error: Unable to process request.');
      setIsPollingProgress(false);
    }
  };

  const handleSubmit = async () => {
    setError('');
    try {
      setIsSubmitting(true);
      const payload = {
        aoi: aoi,
        lidar: selected3DEP,
        naip: selectedNaip,
        model: selectedModel,
      };
      const response = await fetch('/api/model', {
        method: 'post',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const result = await response.json();
      setIsPollingProgress(true);
      setIsSubmitting(false);
      checkStatus(result.session_id);
    } catch (err) {
      console.error('Error:', err);
      setError('Error: Unable to submit job.');
      setIsSubmitting(false);
    }
  };

  return (
    <div className="control">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSubmit();
        }}
      >
        <fieldset>
          <legend>Select Dataset</legend>
          <label htmlFor="model">Select model:</label>
          <input
            type="radio"
            name="model"
            value="lidar"
            checked={selectedModel == 'lidar'}
            onChange={(e) => {
              setSelectedModel(e.target.value as Model);
              setSelectedNaip(null);
            }}
          />
          LiDAR
          <input
            type="radio"
            name="model"
            value="both"
            checked={selectedModel == 'both'}
            onChange={(e) => setSelectedModel(e.target.value as Model)}
          />
          LiDAR + Spectral
          <h3>3DEP</h3>
          <select
            onChange={(e) => {
              const selected = datasets.point_cloud.find(
                ({ id }) => id === e.target.value
              );
              if (selected) {
                setSelected3DEP(selected);
              }
            }}
            value={selected3DEP?.id || ''}
          >
            <option value="">Select 3DEP dataset</option>
            {datasets.point_cloud.map(({ id }) => (
              <option key={id} value={id}>
                {id}
              </option>
            ))}
          </select>
          {selectedModel === 'both' && (
            <div>
              <h3>NAIP</h3>
              <select
                onChange={(e) => {
                  const selected = datasets.raster.find(
                    ({ id }) => id === e.target.value
                  );
                  if (selected) {
                    setSelectedNaip(selected);
                  }
                }}
                value={selectedNaip?.id || ''}
              >
                <option value="">Select NAIP dataset</option>
                {datasets.raster.map(({ id }) => (
                  <option key={id} value={id}>
                    {id}
                  </option>
                ))}
              </select>
            </div>
          )}
        </fieldset>
        <button
          className="submit-button"
          type="submit"
          disabled={
            isSubmitting ||
            result !== null ||
            isPollingProgress ||
            error.length > 0
          }
        >
          {isSubmitting
            ? 'Submitting job...'
            : isPollingProgress
            ? 'Job submitted'
            : 'Submit job'}
        </button>
      </form>
      {error && (
        <div
          style={{
            color: 'red',
            fontSize: 18,
            fontWeight: 600,
            marginTop: 15,
            maxWidth: 400,
            textAlign: 'left',
            width: '100%',
          }}
        >
          {error}
        </div>
      )}
      {!result && isPollingProgress && (
        <div
          style={{
            fontSize: 18,
            fontWeight: 600,
            marginTop: 15,
            textAlign: 'center',
            width: '100%',
          }}
        >
          Waiting for results...
        </div>
      )}
      {result && result?.[viewMode] && (
        <ViewMode
          result={result}
          viewMode={viewMode}
          setViewMode={setViewMode}
        />
      )}
      {(result || error.length > 0) && (
        <div
          style={{ display: 'flex', flexDirection: 'column', marginTop: 15 }}
        >
          <button
            className="reset-button"
            type="submit"
            disabled={isSubmitting}
            onClick={handleReset}
          >
            Reset
          </button>
        </div>
      )}
    </div>
  );
}
