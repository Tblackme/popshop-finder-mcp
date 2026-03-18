# Vendor Atlas Media (SwiftUI MVP)

This folder contains a lightweight SwiftUI app scaffold for the "media side" of Vendor Atlas:

- local sign-in and dev test access
- organizer/shopper following feed
- public vendor business page
- vendor event share controls
- Shopify inventory highlights

## How To Run

1. In Xcode, create a new iOS App target named `VendorAtlasMedia`.
2. Drag the files from this folder into the new target.
3. Set the deployment target to iOS 17 or newer.
4. Make sure `SwiftData.framework` is available to the target.
5. Run the backend locally, for example at `http://localhost:3001`.
6. Launch the app and use the dev test buttons on the sign-in screen.

## Notes

- The app uses SwiftData as the local offline cache.
- It assumes the backend routes already available in this repo:
  - `/api/auth/signin`
  - `/api/auth/dev-login`
  - `/api/auth/me`
  - `/api/auth/logout`
  - `/api/vendors/{username}`
  - `/api/vendors/{vendor_id}/follow`
  - `/api/shopper/following`
  - `/api/vendor/follower-events`
  - `/api/shopify/me`
  - `/api/shopify/products`
  - `/api/shopify/sync`
  - `/api/shopify/disconnect`
- There is no `.xcodeproj` in this repo yet, so these files are scaffolded source code ready to be added to Xcode.
