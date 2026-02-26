// API methods for managing users 
// Author: Michael B. Lance

//---------------------------------------------------------------------------------------------------------------------------//

import { User } from '@/types/generatorobjects.ts';
import type { UserIntf } from '@/types/generatorobjects.ts';
import { ApiError } from '@/modules/api/errors.ts'
import { api_url } from '@/modules/api/apiV1Methods.ts';

//---------------------------------------------------------------------------------------------------------------------------//

export async function checkAuth(): Promise<boolean> {
	const response = await fetch(`${api_url}/users/check-auth`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
		},
		credentials: 'include',
	});
	if (response.status == 401) return false;
	if (!response.ok) {throw new ApiError(await response.json());}

	return true;
}

//---------------------------------------------------------------------------------------------------------------------------//

export async function getCurrentUser(): Promise<User> {
	const response = await fetch(`${api_url}/users/current-user`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
		},
		credentials: 'include',
	});
	if (!response.ok) throw new ApiError(await response.json());

	return new User(await response.json() as UserIntf);
}

//---------------------------------------------------------------------------------------------------------------------------//

export async function authUser(external_id: string): Promise<User> {
	const response = await fetch(`${api_url}/users/authenticate`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
		},
		body: JSON.stringify({
			'external_id': external_id
		}),
		credentials: 'include',
	});
	if (!response.ok) throw new ApiError(await response.json());

	return new User(await response.json() as UserIntf);
}

//---------------------------------------------------------------------------------------------------------------------------//

export async function deauthUser(): Promise<boolean> {
	const response = await fetch(`${api_url}/users/deauthenticate`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
		},
		credentials: 'include'
	});
	if (!response.ok) throw new ApiError(await response.json());

	return true;
}