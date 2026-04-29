// API methods for managing image objects
// Author: Michael B. Lance

// ---------------------------------------------------------------------------------------------------------------------------

import { Image, Prediction } from '@/types/generatorobjects.ts';
import type { ImageIntf, PredictionIntf } from '@/types/generatorobjects.ts';
import { ApiError } from '@/modules/api/errors.ts'
import { api_url } from '@/modules/api/apiV1Methods.ts';

//---------------------------------------------------------------------------------------------------------------------------

interface AutoCropBatchOptions {
  survey_id: string;
  herd_unit_id: string;
  label: number[];
  model_id: string;
  min_confidence: number;
  batch_size: number;  
}

export async function fetchAutoCropperBatch(options: AutoCropBatchOptions): Promise<[Image[], Prediction[][]]> {
	const params = new URLSearchParams()
  options.label.forEach(id => params.append('label', id.toString()));
  params.append('survey_id', options.survey_id.toString());
  params.append('herd_unit_id', options.herd_unit_id.toString());
  params.append('size', options.batch_size.toString());
  params.append('model_id', options.model_id.toString());
  params.append('min_confidence', options.min_confidence.toString());
  params.append('batch_size', options.batch_size.toString());

  const response = await fetch(`${api_url}/autocropper/batch?${params}`, {
		method: 'GET',
		credentials: 'include',
		headers: {
			'Content-Type': 'application/json',
		},
	});
  if (!response.ok) throw new ApiError(await response.json());

	const resp = await response.json();
	const images: Image[] = [];
	const predictions: Prediction[][] = [];

   for (const img of resp) {
		images.push(new Image(img as ImageIntf));
    const preds: Prediction[] = []
			
    for (const pred of img['predictions']) {
			preds.push(new Prediction(pred as PredictionIntf))
    }
			
    predictions.push(preds);
	} 

	return [images as Image[], predictions as Prediction[][]];

}

//---------------------------------------------------------------------------------------------------------------------------

interface AutoCropOptions {
  image_id: string;
  prediction_ids: string[];
  label_ids: string[];
}

export async function autoCrop(parameters: AutoCropOptions): Promise<boolean> {
  const response = await fetch(`${api_url}/autocropper`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(parameters)
  });
  if (!response.ok) throw new ApiError(await response.json());
  
  return true;
}
