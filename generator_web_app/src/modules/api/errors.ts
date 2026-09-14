// Errors for API
// Author: Michael B. Lance

// ---------------------------------------------------------------------------------------------------------------------------


export type apiError = {
	error: string
	message: string
	code: number
}

export class ApiError extends Error {
    public code: number;
    public error: string;

    constructor(data: apiError) {
        super(data.message); 
        
        this.name = 'ApiError';
        this.code = data.code;
        this.error = data.error;

        if (Error.captureStackTrace) {
            Error.captureStackTrace(this, ApiError);
        }
    }
}