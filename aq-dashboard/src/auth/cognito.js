import { originalFetch } from '../api/fetchInterceptor.js'

// Read from environment variables with fallback to hardcoded defaults.
// The app continues to work even if .env is missing.
const COGNITO_REGION    = import.meta.env.VITE_COGNITO_REGION || 'us-west-1'
const COGNITO_CLIENT_ID = import.meta.env.VITE_COGNITO_CLIENT_ID || '34sjhnv2pj2j8rofp39mpa4gi6'
const COGNITO_ENDPOINT  = `https://cognito-idp.${COGNITO_REGION}.amazonaws.com`

/**
 * Authenticate directly with Cognito using USER_PASSWORD_AUTH.
 * Returns the full AuthenticationResult on success.
 * Throws a human-readable Error on failure.
 *
 * Uses `originalFetch` (the real window.fetch) so the interceptor
 * never tries to attach a Bearer token to this request.
 */
export async function cognitoLogin(email, password) {
  const res = await originalFetch(COGNITO_ENDPOINT + '/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-amz-json-1.1',
      'X-Amz-Target': 'AWSCognitoIdentityProviderService.InitiateAuth',
    },
    body: JSON.stringify({
      AuthFlow:       'USER_PASSWORD_AUTH',
      ClientId:       COGNITO_CLIENT_ID,
      AuthParameters: { USERNAME: email, PASSWORD: password },
    }),
  })

  if (!res.ok) {
    const err  = await res.json()
    const code = err.__type || ''

    if (code.includes('NotAuthorizedException'))
      throw new Error('Incorrect email or password.')
    if (code.includes('UserNotFoundException'))
      throw new Error('No account found with that email.')
    if (code.includes('UserNotConfirmedException'))
      throw new Error('Account not confirmed. Please check your email.')

    throw new Error(err.message || 'Authentication failed.')
  }

  const data = await res.json()
  return data.AuthenticationResult  // { AccessToken, IdToken, … }
}
