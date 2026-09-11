# Kavi's Kitchen --- Coding Agent Knowledge & Implementation Specification

## 1. Project Goal

Build a production-ready web application for **Kavi's Kitchen** to
manage:

-   Customer enquiries and customer master data
-   Customer meal preferences
-   Active/inactive customers
-   Daily meal/order scheduling
-   Breakfast, lunch and dinner order planning
-   Subscription and ad-hoc/on-demand orders
-   Driver delivery assignment
-   Driver live location tracking
-   Google Maps customer locations and navigation
-   Delivery status tracking
-   Completed/cancelled/failed deliveries
-   Monthly business dashboard and analytics
-   Role-based access for Super Admin, Admin and Driver

The application must be implemented as a **separate frontend and
backend**:

``` text
kavis-kitchen/
├── frontend/       # React application
├── backend/        # FastAPI application
├── README.md
├── .env.example
└── docker-compose.yml   # optional local MongoDB alternative; production uses MongoDB Atlas
```

Technology stack:

-   Frontend: React + Vite + TypeScript
-   UI: Tailwind CSS + shadcn/ui or equivalent accessible component
    system
-   Icons: Lucide React
-   Charts: Recharts
-   Maps: Google Maps JavaScript API / Google Maps Directions API
-   Backend: Python + FastAPI
-   Database: MongoDB Atlas
-   ODM/driver: Motor/PyMongo with Pydantic models
-   Authentication: JWT access/refresh tokens
-   Password hashing: Argon2 or bcrypt
-   Real-time tracking: WebSocket
-   API documentation: FastAPI OpenAPI/Swagger
-   Validation: Pydantic
-   HTTP client: Axios or fetch wrapper
-   State management: React Query/TanStack Query + lightweight local
    auth state
-   Date handling: date-fns
-   Notifications: toast notifications
-   Deployment-ready configuration using environment variables

------------------------------------------------------------------------

# 2. Branding and UI Direction

Use the previously uploaded **Kavi's Kitchen logo** as the primary
application logo.

Reference asset:

-   `Kavi’s Kitchen Chef Emblem.png`
-   Transparent PNG logo with chef hat, yellow/orange circular emblem,
    fork/spoon and Kavi's Kitchen wordmark.

The brand visual language should follow the existing Kavi's Kitchen
materials:

-   Warm mustard/yellow/gold
-   Dark charcoal/black
-   Cream/off-white
-   Deep green as a supporting color
-   Small red/orange accents only where useful
-   Rounded cards
-   Soft shadows
-   Clean modern restaurant-management dashboard
-   Rustic-modern visual character
-   Avoid excessive gradients
-   Use the logo subtly; do not make it oversized

Suggested design tokens:

``` text
Primary:        Mustard / Golden Yellow
Secondary:      Deep Green
Background:     Warm Cream / Off White
Text Primary:   Charcoal
Text Secondary: Muted Gray
Success:        Green
Warning:        Amber
Danger:         Red
Info:            Blue
```

The UI must be elegant, responsive and professional rather than looking
like a generic admin template.

------------------------------------------------------------------------

# 3. UX Principles

The application must be easy for a non-technical kitchen/admin operator.

Priorities:

1.  Fast data entry
2.  Minimal clicks
3.  Clear meal status
4.  Clear delivery status
5.  Mobile-friendly driver interface
6.  Desktop/tablet-friendly admin interface
7.  Strong visual hierarchy
8.  Confirmation before destructive actions
9.  Search and filtering everywhere appropriate
10. No loss of unsaved data
11. Loading skeletons instead of blank screens
12. Helpful empty states
13. Clear validation messages
14. Toast confirmation after successful actions

Use subtle animations:

-   Page transitions
-   Card hover
-   Modal entrance
-   Table row highlight
-   Status badge transitions
-   Map marker pulse for active driver
-   Dashboard number count-up animation
-   Skeleton loading
-   Button loading state
-   Drawer/modal slide-in

Animations must never slow down business operations.

------------------------------------------------------------------------

# 4. User Roles and Permissions

## 4.1 Super Admin

Full system access.

Can:

-   View dashboard
-   Manage admins
-   Manage drivers
-   Create/edit/deactivate users
-   Manage customers
-   Manage meal plans
-   Manage menu items
-   Manage daily meal schedules
-   Manage orders
-   Assign drivers
-   Reassign drivers
-   View live driver locations
-   View delivery history
-   View completed orders
-   View cancelled orders
-   View reports
-   Configure application settings
-   Configure delivery zones
-   Configure pricing
-   View audit logs
-   Reset passwords
-   Activate/deactivate users

## 4.2 Admin

Operational management access.

Can:

-   View dashboard
-   Manage customers
-   Create/edit customer details
-   Activate/deactivate customers
-   Record enquiries
-   Manage meal preferences
-   Create/edit daily meal orders
-   View upcoming/current orders
-   Assign drivers
-   View driver delivery status
-   View live driver location
-   View completed deliveries
-   View cancelled/failed deliveries
-   View reports

Cannot:

-   Manage Super Admin
-   Manage system-level settings unless explicitly permitted
-   Change critical security settings
-   Delete audit logs

## 4.3 Driver

Mobile-first delivery access.

Can:

-   Login
-   View today's assigned deliveries
-   View delivery sequence
-   View customer details needed for delivery
-   View customer address
-   Open Google Maps navigation
-   Start delivery
-   Share live location while delivery is active
-   Mark order as delivered
-   Mark failed delivery
-   Record delivery note
-   Call customer
-   Open WhatsApp if required
-   View completed deliveries for the current day

Cannot:

-   View all customers
-   Edit customer master data
-   Change pricing
-   View financial reports
-   Assign orders
-   Manage users

------------------------------------------------------------------------

# 5. Authentication

Implement secure authentication.

## Login

Fields:

-   Username/email/phone
-   Password

Backend returns:

-   Access token
-   Refresh token
-   User profile
-   Role
-   Permissions

Frontend must route users based on role.

Example:

``` text
/login

SUPER_ADMIN -> /admin/dashboard
ADMIN       -> /admin/dashboard
DRIVER      -> /driver/today
```

Implement:

-   JWT authentication
-   Refresh token rotation
-   Password hashing
-   Account active/inactive status
-   Login failure handling
-   Logout
-   Token expiration handling
-   Protected routes
-   Role-based API authorization

Never trust frontend role checks alone. Backend must enforce
permissions.

------------------------------------------------------------------------

# 6. Customer Management Module

Route:

``` text
/admin/customers
```

## Customer Creation

Required/important fields:

### Basic information

-   Customer name
-   Phone number
-   Alternate phone number
-   WhatsApp number
-   Customer type:
    -   Individual
    -   Family
    -   Office/Manpower
    -   Other
-   Active / Inactive

### Address

Support both:

1.  Manual address
2.  Google Maps location picker

Fields:

-   Address line
-   Area/locality
-   Landmark
-   City
-   Pincode
-   Latitude
-   Longitude
-   Google Place ID
-   Location accuracy if available

Google location flow:

``` text
Click "Select Location"
        ↓
Google Map opens
        ↓
Search place/address OR move marker
        ↓
Confirm location
        ↓
Capture:
  latitude
  longitude
  formatted address
  place ID
        ↓
Save customer
```

Never store only the Google Maps URL. Store latitude/longitude and place
ID as structured data.

### Meal preference

Allow:

-   Veg
-   Non-Veg
-   Egg
-   Custom

Meal sessions:

-   Breakfast
-   Lunch
-   Dinner

Preferences:

-   Normal spice
-   Mild spice
-   Rice preference
-   Food exclusions
-   Allergy/food note
-   General delivery note

Do not collect sensitive medical information unless genuinely required.
If food allergy information is collected, treat it as operationally
important and display it clearly to kitchen/admin.

### Customer status

-   Active
-   Inactive

Inactive customers should not automatically appear in new order
planning.

------------------------------------------------------------------------

# 7. Customer Enquiry Management

Create a dedicated enquiry workflow.

Route:

``` text
/admin/enquiries
```

Statuses:

``` text
NEW
CONTACTED
QUOTED
FOLLOW_UP
CONFIRMED
REJECTED
CONVERTED
CLOSED
```

Fields:

-   Customer name
-   Phone
-   Enquiry date/time
-   Requested meal
-   Requested date
-   Number of persons
-   Veg/non-veg
-   Subscription/ad-hoc
-   Delivery location
-   Quoted price
-   Notes
-   Follow-up date
-   Assigned admin
-   Conversion status

When enquiry becomes confirmed:

``` text
Enquiry
   ↓
Create/identify Customer
   ↓
Create Meal Plan / Order
   ↓
Create daily order occurrences
```

Do not duplicate customer records if the phone number already exists.

------------------------------------------------------------------------

# 8. Meal Plan Management

Create configurable meal plans.

Example existing business plans:

``` text
Veg Full Day
₹5,499/month
Breakfast + Lunch + Dinner
Monday–Saturday
26 service days

Non-Veg Full Day
₹6,499/month
Breakfast + Lunch + Dinner
Monday–Saturday
26 service days
```

Also support:

-   Breakfast only
-   Lunch only
-   Dinner only
-   Breakfast + Lunch
-   Lunch + Dinner
-   Breakfast + Dinner
-   Custom plan

Plan configuration should contain:

-   Plan name
-   Meal sessions
-   Veg/non-veg
-   Price
-   Billing cycle
-   Service days
-   Delivery eligibility
-   Active/inactive
-   Description

Do not hard-code pricing in React.

------------------------------------------------------------------------

# 9. Order / Meal Session Planning

This is a core module.

Route:

``` text
/admin/orders
```

Provide two modes:

## 9.1 Calendar mode

Show:

-   Today
-   Tomorrow
-   Week
-   Month

## 9.2 Grid mode

Rows:

``` text
Customer
```

Columns:

``` text
Date
Breakfast
Lunch
Dinner
```

Example:

``` text
Customer A | 11 Sep | ✓ | ✓ | ✓
Customer B | 11 Sep | - | ✓ | ✓
Customer C | 11 Sep | ✓ | - | ✓
```

Allow admin to select/unselect meal sessions.

For each selected session store:

-   Customer
-   Date
-   Meal session
-   Meal type
-   Quantity
-   Order type
-   Delivery required
-   Delivery address
-   Driver
-   Status
-   Notes

Statuses:

``` text
PLANNED
CONFIRMED
PREPARING
READY
ASSIGNED
OUT_FOR_DELIVERY
DELIVERED
FAILED
CANCELLED
SKIPPED
```

When admin clicks Save:

-   Validate selections
-   Show confirmation summary
-   Persist changes
-   Create/update order records
-   Avoid duplicate order occurrences

------------------------------------------------------------------------

# 10. Subscription vs Ad-Hoc Orders

The application must support both.

## Subscription

Example:

``` text
Customer A
Veg Full Day
26 service days
Breakfast + Lunch + Dinner
```

The system generates expected daily meal occurrences.

## Ad-Hoc / On-demand

Example:

``` text
Customer calls at 10:00 AM
Lunch for 3 people
Delivery required
```

Create a one-time order.

Fields:

-   Order date
-   Meal session
-   Quantity
-   Meal type
-   Customer
-   Address
-   Delivery charge
-   Total amount
-   Payment status
-   Notes

Do not force all orders into subscription logic.

------------------------------------------------------------------------

# 11. Bulk / Manpower Orders

Support commercial/workplace meal orders.

Example:

``` text
Company / Worksite
20 people
Lunch
Non-Veg
Daily headcount confirmation before 10:00 AM
```

Fields:

-   Organization/site name
-   Contact person
-   Phone
-   Location
-   Expected headcount
-   Confirmed headcount
-   Meal type
-   Menu
-   Price per head
-   Delivery charge
-   Confirmation cutoff time
-   Special instructions

Allow quantity to change before cutoff.

After cutoff, lock the quantity unless an admin explicitly overrides it.

Important business rule:

> Confirmed quantity is the quantity used for preparation and billing
> unless an authorized admin overrides it.

------------------------------------------------------------------------

# 12. Menu Management

Route:

``` text
/admin/menu
```

Admin can configure:

-   Menu item name
-   Tamil name
-   Category
-   Veg/non-veg
-   Meal session
-   Description
-   Active/inactive
-   Image
-   Approximate cost
-   Tags

Categories:

-   Breakfast
-   Main course
-   Side dish
-   Curry
-   Poriyal
-   Kootu
-   Rasam
-   Chutney
-   Dessert
-   Non-veg
-   Beverage

Create weekly menu templates.

The application should allow menu rotation without changing historical
orders.

Historical orders must retain the menu that was actually assigned at
that time.

------------------------------------------------------------------------

# 13. Driver Management

Route:

``` text
/admin/drivers
```

Fields:

-   Driver name
-   Phone
-   Username/email
-   Password reset
-   Vehicle type
-   Vehicle number
-   Driving status
-   Active/inactive
-   Current availability
-   Last known location
-   Last location timestamp

Driver states:

``` text
OFFLINE
AVAILABLE
ON_DELIVERY
PAUSED
```

------------------------------------------------------------------------

# 14. Driver Today's Delivery Screen

Driver route:

``` text
/driver/today
```

Mobile-first design.

At top:

-   Driver name
-   Current date
-   Availability status
-   Number of pending deliveries
-   Completed count

Delivery cards should show:

-   Sequence number
-   Customer name
-   Meal session
-   Quantity
-   Address
-   Distance
-   Delivery note
-   Customer phone
-   Call button
-   Navigate button
-   Start Delivery button
-   Complete button

Example:

``` text
#01
Customer A
Lunch • 1 Meal

2.4 km
Near XYZ School

[Call] [Navigate]

[START DELIVERY]
```

------------------------------------------------------------------------

# 15. Driver Location Permission

When driver starts delivery:

``` text
Driver clicks START DELIVERY
        ↓
Check browser geolocation permission
        ↓
If denied:
    Show clear permission instructions
        ↓
If allowed:
    Start location tracking
        ↓
Send coordinates to backend
        ↓
Admin dashboard receives live updates
```

Use browser:

``` javascript
navigator.geolocation.watchPosition(...)
```

Do not continuously track the driver when they are not actively working.

Tracking should be enabled only when:

-   Driver is on an active delivery, OR
-   Driver explicitly starts a delivery shift.

------------------------------------------------------------------------

# 16. Live Driver Tracking

Admin dashboard must display active drivers on Google Maps.

Map should show:

-   Driver marker
-   Driver name
-   Driver status
-   Last updated time
-   Current active order
-   Delivery destination
-   Route
-   ETA where possible

Driver location flow:

``` text
Driver Browser
     ↓
Geolocation API
     ↓
WebSocket
     ↓
FastAPI WebSocket Manager
     ↓
MongoDB latest location
     ↓
Admin WebSocket
     ↓
Google Map marker updates
```

Do not write every GPS update to MongoDB indefinitely.

Use two layers:

### Latest location

Store one current location per driver.

### Location history

Store sampled points only, e.g. every 10--30 seconds or when moved a
meaningful distance.

Configurable:

``` text
LOCATION_UPDATE_INTERVAL_SECONDS=10
LOCATION_MIN_DISTANCE_METERS=20
```

------------------------------------------------------------------------

# 17. Delivery Completion

Driver clicks:

``` text
COMPLETE DELIVERY
```

Require confirmation.

Optional/required fields:

-   Delivered time
-   Delivery note
-   Recipient name
-   Proof of delivery photo if business later requires it
-   Customer signature if required later

Recommended initial implementation:

-   Delivery note
-   Recipient name
-   Optional photo

On completion:

``` text
OUT_FOR_DELIVERY
      ↓
DELIVERED
      ↓
Stop live location tracking for that delivery
```

Admin should see the completion immediately.

------------------------------------------------------------------------

# 18. Failed Delivery

Do not allow the driver to simply mark an order as failed without a
reason.

Reasons:

-   Customer unavailable
-   Wrong address
-   Phone unreachable
-   Customer cancelled
-   Location inaccessible
-   Other

Require a note for Other.

Status:

``` text
FAILED
```

Admin can reassign/retry.

------------------------------------------------------------------------

# 19. Delivery Assignment

Admin can:

-   Assign one order to driver
-   Bulk assign orders
-   Reassign
-   Change delivery sequence
-   Filter unassigned orders

Suggested assignment view:

``` text
UNASSIGNED
DRIVER 1
DRIVER 2
DRIVER 3
```

Drag/drop assignment is desirable but not mandatory for first version.

------------------------------------------------------------------------

# 20. Route Optimization Enhancement

Add a route planning enhancement.

Admin should be able to:

-   Group deliveries by location
-   Sort by distance
-   Generate optimized sequence
-   Detect nearby customers
-   Detect out-of-route deliveries

Do not automatically change a manually assigned route without
confirmation.

Use Google Maps Directions/Distance Matrix or current Google Maps
routing capabilities where appropriate.

------------------------------------------------------------------------

# 21. Dashboard

Route:

``` text
/admin/dashboard
```

Dashboard cards:

-   Total active customers
-   New enquiries
-   Today's orders
-   Pending deliveries
-   Completed deliveries
-   Failed deliveries
-   Active drivers
-   Revenue today
-   Monthly revenue
-   Subscription customers
-   Ad-hoc orders

Charts:

### Monthly revenue

Line/bar chart.

### Orders by meal session

``` text
Breakfast
Lunch
Dinner
```

### Orders by meal type

``` text
Veg
Non-Veg
Egg
```

### Delivery status

``` text
Pending
Out for delivery
Delivered
Failed
Cancelled
```

### Customer growth

New customers per month.

### Subscription vs Ad-hoc

Donut/pie chart.

### Delivery performance

-   Average delivery completion time
-   Successful delivery %
-   Failed delivery %
-   Orders per driver

All dashboard data must be date-filterable.

Filters:

-   Today
-   This week
-   This month
-   Custom range

------------------------------------------------------------------------

# 22. Finance / Pricing

Create a simple operational finance module.

Track:

-   Order subtotal
-   Delivery charge
-   Discount
-   Final amount
-   Payment status
-   Payment method

Payment statuses:

``` text
PENDING
PAID
PARTIAL
REFUNDED
CANCELLED
```

Payment methods:

``` text
CASH
UPI
BANK_TRANSFER
ONLINE
OTHER
```

Do not integrate payment gateway in V1 unless specifically requested.

------------------------------------------------------------------------

# 23. Delivery Pricing Configuration

Do not hard-code delivery rates.

Create settings:

``` text
FREE_DELIVERY_RADIUS_KM = 3

MIN_DELIVERY_CHARGE = 30

OUTSIDE_RADIUS_RATE_PER_KM = configurable

STANDARD_ROUTE_DROP_PAYOUT = 15

ADDITIONAL_NEARBY_DROP_PAYOUT = 10

DRIVER_LONG_DISTANCE_RATE = configurable
```

The business can change these values later from Super Admin settings.

------------------------------------------------------------------------

# 24. Notifications

V1 should support internal notifications.

Admin notifications:

-   New enquiry
-   New order
-   Driver started delivery
-   Delivery completed
-   Failed delivery
-   Driver offline
-   Location unavailable

Driver notifications:

-   New assignment
-   Order changed
-   Order cancelled
-   Route changed

Design the backend so SMS/WhatsApp integration can be added later.

------------------------------------------------------------------------

# 25. Search and Filters

Every major list must have:

-   Search
-   Date filter
-   Status filter
-   Meal filter
-   Customer filter
-   Driver filter where applicable
-   Pagination
-   Sort
-   Clear filters

Customer search:

-   Name
-   Phone
-   Area

Order search:

-   Customer
-   Order ID
-   Date
-   Status
-   Meal session

------------------------------------------------------------------------

# 26. Audit Log

Create audit logging.

Track:

-   Login
-   Customer created
-   Customer edited
-   Customer activated/deactivated
-   Order created
-   Order changed
-   Order cancelled
-   Driver assigned
-   Driver reassigned
-   Delivery started
-   Delivery completed
-   Pricing changed
-   User created/deactivated

Audit fields:

``` text
user_id
role
action
entity_type
entity_id
old_value
new_value
timestamp
ip_address
```

Never allow normal admins to delete audit records.

------------------------------------------------------------------------

# 27. MongoDB Collections

Suggested collections:

``` text
users
roles
customers
customer_addresses
customer_preferences
enquiries
meal_plans
subscriptions
menus
menu_templates
orders
order_items
delivery_assignments
drivers
driver_locations
payments
notifications
audit_logs
app_settings
```

Avoid unnecessary duplication.

------------------------------------------------------------------------

# 28. Suggested Core Schemas

## User

``` json
{
  "_id": "ObjectId",
  "name": "Admin User",
  "phone": "string",
  "email": "string",
  "password_hash": "string",
  "role": "SUPER_ADMIN | ADMIN | DRIVER",
  "is_active": true,
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

## Customer

``` json
{
  "_id": "ObjectId",
  "name": "Customer Name",
  "phone": "string",
  "alternate_phone": "string",
  "customer_type": "INDIVIDUAL | FAMILY | OFFICE | OTHER",
  "status": "ACTIVE | INACTIVE",
  "address": {
    "formatted_address": "string",
    "area": "string",
    "landmark": "string",
    "city": "string",
    "pincode": "string",
    "latitude": 0,
    "longitude": 0,
    "place_id": "string"
  },
  "meal_preferences": {
    "food_type": "VEG | NON_VEG | EGG | CUSTOM",
    "sessions": ["BREAKFAST", "LUNCH", "DINNER"],
    "spice": "MILD | NORMAL",
    "notes": "string"
  },
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

## Order

``` json
{
  "_id": "ObjectId",
  "order_number": "KK-20260910-0001",
  "customer_id": "ObjectId",
  "order_date": "date",
  "meal_session": "BREAKFAST | LUNCH | DINNER",
  "order_type": "SUBSCRIPTION | AD_HOC | BULK",
  "meal_type": "VEG | NON_VEG | EGG | CUSTOM",
  "quantity": 1,
  "unit_price": 0,
  "subtotal": 0,
  "delivery_charge": 0,
  "discount": 0,
  "total": 0,
  "status": "PLANNED",
  "delivery_required": true,
  "delivery_address": {},
  "driver_id": null,
  "notes": "",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

## Delivery Assignment

``` json
{
  "_id": "ObjectId",
  "order_id": "ObjectId",
  "driver_id": "ObjectId",
  "sequence": 1,
  "status": "ASSIGNED | OUT_FOR_DELIVERY | DELIVERED | FAILED",
  "assigned_at": "datetime",
  "started_at": null,
  "completed_at": null,
  "delivery_note": "",
  "recipient_name": "",
  "proof_photo_url": null
}
```

## Driver Location

``` json
{
  "_id": "ObjectId",
  "driver_id": "ObjectId",
  "latitude": 0,
  "longitude": 0,
  "accuracy": 0,
  "heading": 0,
  "speed": 0,
  "timestamp": "datetime",
  "active_order_id": null
}
```

------------------------------------------------------------------------

# 29. Backend Folder Structure

Use a clean modular FastAPI architecture.

``` text
backend/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   ├── database.py
│   │   ├── permissions.py
│   │   └── websocket_manager.py
│   ├── api/
│   │   ├── router.py
│   │   └── v1/
│   │       ├── auth.py
│   │       ├── users.py
│   │       ├── customers.py
│   │       ├── enquiries.py
│   │       ├── meal_plans.py
│   │       ├── subscriptions.py
│   │       ├── menus.py
│   │       ├── orders.py
│   │       ├── drivers.py
│   │       ├── deliveries.py
│   │       ├── locations.py
│   │       ├── dashboard.py
│   │       ├── payments.py
│   │       ├── settings.py
│   │       └── audit_logs.py
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── repositories/
│   ├── dependencies/
│   ├── utils/
│   └── tests/
├── requirements.txt
├── .env.example
└── README.md
```

Use service/repository separation so business rules are not buried
inside API route functions.

------------------------------------------------------------------------

# 30. Frontend Folder Structure

``` text
frontend/
├── src/
│   ├── app/
│   ├── components/
│   │   ├── ui/
│   │   ├── layout/
│   │   ├── forms/
│   │   ├── tables/
│   │   ├── maps/
│   │   └── charts/
│   ├── features/
│   │   ├── auth/
│   │   ├── customers/
│   │   ├── enquiries/
│   │   ├── meal-plans/
│   │   ├── subscriptions/
│   │   ├── orders/
│   │   ├── drivers/
│   │   ├── deliveries/
│   │   ├── dashboard/
│   │   └── settings/
│   ├── pages/
│   ├── routes/
│   ├── services/
│   ├── hooks/
│   ├── lib/
│   ├── types/
│   ├── utils/
│   ├── assets/
│   │   └── logo.png
│   ├── App.tsx
│   └── main.tsx
├── public/
├── package.json
├── .env.example
└── README.md
```

------------------------------------------------------------------------

# 31. Admin Navigation

Sidebar:

``` text
Dashboard

Operations
├── Enquiries
├── Customers
├── Meal Planner
├── Orders
├── Deliveries

Menu & Plans
├── Meal Plans
├── Menu
├── Weekly Menu

Delivery
├── Drivers
├── Live Tracking
├── Delivery History

Reports
├── Sales
├── Orders
├── Delivery Performance
├── Customer Reports

Administration
├── Users
├── Settings
├── Audit Logs
```

Driver sidebar/navigation:

``` text
Today
Active Delivery
Completed
Profile
Logout
```

------------------------------------------------------------------------

# 32. Important Order Workflow

## Subscription order flow

``` text
Customer Enquiry
      ↓
Customer Created
      ↓
Meal Plan Selected
      ↓
Subscription Activated
      ↓
Service Calendar Generated
      ↓
Daily Orders Created
      ↓
Admin Reviews Meal Planner
      ↓
Kitchen Prepares
      ↓
Order Ready
      ↓
Driver Assigned
      ↓
Driver Starts Delivery
      ↓
Live Location
      ↓
Delivered
      ↓
Daily Order Completed
```

## Ad-hoc order flow

``` text
Customer Calls / WhatsApp
      ↓
Admin creates order
      ↓
Confirm quantity
      ↓
Kitchen prepares
      ↓
Assign driver
      ↓
Driver starts
      ↓
Live tracking
      ↓
Delivered / Failed
```

------------------------------------------------------------------------

# 33. Meal Planner UX

This screen is extremely important.

Provide:

### Date selector

``` text
< Previous Day | Today | Tomorrow >
```

### Meal tabs

``` text
All | Breakfast | Lunch | Dinner
```

### Customer grid

``` text
Customer | Type | Breakfast | Lunch | Dinner | Delivery | Driver | Status
```

Use compact status chips.

Examples:

``` text
✓ Selected
— Not Required
⏳ Pending
🚚 Out for Delivery
✓ Delivered
```

Bulk actions:

-   Select all breakfast
-   Select all lunch
-   Select all dinner
-   Assign driver
-   Mark ready
-   Cancel selected

Always confirm bulk actions.

------------------------------------------------------------------------

# 34. Driver Map UX

Driver mobile screen:

``` text
--------------------------------
Kavi's Kitchen
Today's Deliveries: 8
--------------------------------

NEXT DELIVERY

Customer A
Lunch • 2 meals

📍 2.1 km
[ Navigate ]

[ START DELIVERY ]

--------------------------------
UP NEXT
Customer B
Customer C
...
```

When active:

``` text
LIVE DELIVERY

Customer A

● Tracking active

[ OPEN GOOGLE MAPS ]

[ COMPLETE DELIVERY ]
[ REPORT ISSUE ]
```

------------------------------------------------------------------------

# 35. Admin Live Tracking UX

Map screen:

Left panel:

``` text
ACTIVE DRIVERS

Driver 1
● On delivery
Customer A
Updated 5 sec ago

Driver 2
● Available
Updated 20 sec ago
```

Right/main area:

Google Map.

Click driver marker:

``` text
Driver: Kumar
Status: On Delivery
Order: KK-20260910-0007
Customer: Customer A
Distance remaining: ...
Last updated: 5 sec ago
```

Use marker animation only while active.

If location becomes stale:

``` text
Last updated 2 minutes ago
```

Do not show a false "live" state.

------------------------------------------------------------------------

# 36. Google Maps Requirements

Environment variable:

``` text
VITE_GOOGLE_MAPS_API_KEY=
```

Backend if needed:

``` text
GOOGLE_MAPS_API_KEY=
```

Enable only required APIs.

Frontend features:

-   Places search
-   Map marker
-   Current location
-   Directions/navigation handoff
-   Customer location
-   Driver location
-   Route display

Do not expose unrestricted server secrets to frontend.

Restrict Google API keys by:

-   HTTP referrer for browser key
-   API restrictions
-   Application restrictions

------------------------------------------------------------------------

# 37. API Design

Base URL:

``` text
/api/v1
```

Example endpoints:

``` text
POST   /auth/login
POST   /auth/refresh
POST   /auth/logout
GET    /auth/me

GET    /customers
POST   /customers
GET    /customers/{id}
PUT    /customers/{id}
PATCH  /customers/{id}/status

GET    /enquiries
POST   /enquiries
PUT    /enquiries/{id}
POST   /enquiries/{id}/convert

GET    /meal-plans
POST   /meal-plans
PUT    /meal-plans/{id}

GET    /orders
POST   /orders
PUT    /orders/{id}
PATCH  /orders/{id}/status

GET    /deliveries/today
POST   /deliveries/{id}/assign
POST   /deliveries/{id}/start
POST   /deliveries/{id}/complete
POST   /deliveries/{id}/fail

GET    /drivers
POST   /drivers
PUT    /drivers/{id}

GET    /dashboard/summary
GET    /dashboard/revenue
GET    /dashboard/orders
GET    /dashboard/delivery-performance

WS     /ws/driver-location/{driver_id}
WS     /ws/admin-tracking
```

------------------------------------------------------------------------

# 38. WebSocket Rules

Driver sends:

``` json
{
  "latitude": 10.123,
  "longitude": 78.456,
  "accuracy": 12,
  "heading": 90,
  "speed": 8,
  "timestamp": "..."
}
```

Backend broadcasts:

``` json
{
  "driver_id": "...",
  "latitude": 10.123,
  "longitude": 78.456,
  "status": "ON_DELIVERY",
  "order_id": "...",
  "timestamp": "..."
}
```

Handle:

-   Disconnect
-   Reconnect
-   Permission denied
-   GPS unavailable
-   Browser background limitations
-   Stale location
-   Network loss

Never crash the delivery flow because WebSocket is unavailable.

The order must still be completable.

------------------------------------------------------------------------

# 39. Security Requirements

Implement:

-   Password hashing
-   JWT
-   Refresh tokens
-   Role-based authorization
-   Request validation
-   MongoDB injection-safe queries
-   CORS configuration
-   Rate limiting on authentication endpoints
-   Secure headers
-   Audit logs
-   No secrets in source code
-   Environment variables
-   Proper error handling
-   No stack traces in production responses
-   Object-level authorization checks

A driver must never be able to request arbitrary customer data by
changing an ID in the URL.

------------------------------------------------------------------------

# 40. Error Handling

Backend standard response format:

``` json
{
  "success": false,
  "message": "Human readable message",
  "error_code": "CUSTOMER_NOT_FOUND",
  "details": {}
}
```

Frontend should show friendly messages.

Never show raw Python exceptions to users.

------------------------------------------------------------------------

# 41. Validation

Customer:

-   Name required
-   Phone required
-   Phone format validation
-   Address required if delivery enabled
-   Latitude/longitude required for map delivery
-   Meal preference validation

Order:

-   Customer required
-   Date required
-   Meal session required
-   Quantity \> 0
-   Price \>= 0

Driver completion:

-   Delivery must be assigned
-   Delivery must be started before completion
-   Require recipient/notes according to configuration

------------------------------------------------------------------------

# 42. Database Indexes

Create indexes for:

``` text
customers.phone
customers.status
customers.name
orders.order_date
orders.status
orders.customer_id
orders.driver_id
orders.meal_session
orders.order_number
delivery_assignments.driver_id
delivery_assignments.status
driver_locations.driver_id
driver_locations.timestamp
enquiries.status
enquiries.phone
```

Use compound indexes where useful.

------------------------------------------------------------------------

# 43. Timezone

The business operates in India.

Use:

``` text
Asia/Kolkata
```

Store timestamps consistently in UTC where practical and convert to
Asia/Kolkata in UI/business rules.

Meal dates must not shift because of timezone conversion.

------------------------------------------------------------------------

# 44. Scheduled Jobs

Backend should support scheduled/background jobs for:

-   Generating subscription daily orders
-   Cleaning stale driver locations
-   Notification processing
-   Daily delivery summaries
-   Monthly reports

Use APScheduler/Celery/RQ only if justified.

For the initial version, prefer a simple robust scheduler/background
mechanism rather than adding unnecessary infrastructure.

------------------------------------------------------------------------

# 45. Data Integrity Rules

Important:

1.  No duplicate customer by normalized phone unless admin explicitly
    creates a separate household/site profile.
2.  No duplicate subscription order for the same customer/date/session.
3.  Completed orders cannot be silently edited.
4.  Cancelled orders require audit logging.
5.  Historical orders must preserve historical prices.
6.  Historical orders must preserve the menu assigned at that time.
7.  Deactivating a customer must not delete historical records.
8.  Deactivating a driver must not delete delivery history.
9.  Driver cannot complete an unassigned order.
10. Driver cannot complete an order belonging to another driver unless
    authorized reassignment occurred.
11. Delivery tracking stops after completion.
12. Bulk updates must be transactional from the application's business
    perspective.

------------------------------------------------------------------------

# 46. Responsive Design

Admin:

-   Desktop-first
-   Tablet compatible
-   Mobile usable

Driver:

-   Mobile-first
-   Large buttons
-   Minimal text entry
-   High contrast
-   One-handed operation where possible

Minimum target:

``` text
360px mobile width
768px tablet
1024px desktop
1440px large desktop
```

------------------------------------------------------------------------

# 47. Accessibility

Use:

-   Semantic HTML
-   Keyboard navigation
-   Visible focus
-   ARIA labels where required
-   Proper color contrast
-   Tooltips for unfamiliar icons
-   Don't rely on color alone for status

------------------------------------------------------------------------

# 48. Performance

Frontend:

-   Lazy load pages
-   Code splitting
-   Query caching
-   Debounced search
-   Pagination
-   Avoid unnecessary map rerenders
-   Throttle GPS updates

Backend:

-   Pagination
-   Indexed queries
-   Projection where useful
-   Avoid N+1 queries
-   Async I/O
-   Background processing where appropriate

Dashboard APIs should aggregate efficiently.

------------------------------------------------------------------------

# 49. Testing

Backend tests:

-   Authentication
-   Role permissions
-   Customer CRUD
-   Enquiry conversion
-   Order creation
-   Duplicate order prevention
-   Driver assignment
-   Delivery state transitions
-   Failed delivery
-   Dashboard aggregation
-   WebSocket location handling

Frontend tests:

-   Login
-   Role routing
-   Customer form
-   Google location selection
-   Meal planner
-   Driver delivery flow
-   Completion flow
-   Live map updates

End-to-end scenarios:

### Scenario A

``` text
Create customer
→ Select Google location
→ Save
→ Add breakfast/lunch/dinner
→ Save planner
→ Assign driver
→ Driver starts
→ Location visible to admin
→ Driver completes
→ Admin sees delivered
```

### Scenario B

``` text
Create enquiry
→ Quote
→ Convert
→ Customer created
→ Subscription created
→ Daily orders generated
```

### Scenario C

``` text
Ad-hoc lunch
→ Assign driver
→ Start
→ GPS tracking
→ Complete
```

------------------------------------------------------------------------

# 50. Seed Data

Create development seed data:

### Users

``` text
Super Admin
Admin
Driver 1
Driver 2
```

### Customers

At least 10 demo customers with different locations.

### Orders

Create today's:

-   Breakfast
-   Lunch
-   Dinner
-   Pending
-   Out-for-delivery
-   Delivered
-   Failed

### Menu

Create sample South Indian menus.

Do not use real customer personal information.

------------------------------------------------------------------------

# 51. Environment Variables

## Backend `.env.example`

``` env
APP_NAME=Kavi's Kitchen
ENVIRONMENT=development
DEBUG=true

MONGODB_URI=mongodb+srv://...
MONGODB_DB_NAME=kavis_kitchen

JWT_SECRET_KEY=change-me
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

GOOGLE_MAPS_API_KEY=

CORS_ORIGINS=http://localhost:5173

LOCATION_UPDATE_INTERVAL_SECONDS=10
LOCATION_MIN_DISTANCE_METERS=20

FREE_DELIVERY_RADIUS_KM=3
MIN_DELIVERY_CHARGE=30
STANDARD_ROUTE_DROP_PAYOUT=15
ADDITIONAL_NEARBY_DROP_PAYOUT=10
```

## Frontend `.env.example`

``` env
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_GOOGLE_MAPS_API_KEY=
```

Never commit real `.env` files.

------------------------------------------------------------------------

# 52. Local Development

Backend:

``` bash
cd backend

python -m venv venv

# Windows
venv\Scripts\activate

pip install -r requirements.txt

uvicorn app.main:app --reload --port 8000
```

Frontend:

``` bash
cd frontend

npm install

npm run dev
```

Expected:

``` text
Frontend:
http://localhost:5173

Backend:
http://localhost:8000

Swagger:
http://localhost:8000/docs
```

------------------------------------------------------------------------

# 53. Production Readiness

Provide:

-   Production `.env.example`
-   Build scripts
-   Health endpoint
-   Logging
-   Error handling
-   CORS configuration
-   MongoDB connection health
-   API versioning
-   Docker support
-   README deployment instructions

Health:

``` text
GET /health
```

Response:

``` json
{
  "status": "ok",
  "database": "connected"
}
```

------------------------------------------------------------------------

# 54. Docker Optional Structure

``` text
docker-compose.yml

services:
  backend:
    build: ./backend

  frontend:
    build: ./frontend
```

MongoDB production must use **MongoDB Atlas**.

Do not require local MongoDB when `MONGODB_URI` points to Atlas.

------------------------------------------------------------------------

# 55. UI Pages Required in V1

## Authentication

-   Login

## Admin

-   Dashboard
-   Enquiries
-   Customers
-   Customer Details
-   Meal Planner
-   Orders
-   Order Details
-   Deliveries
-   Drivers
-   Driver Details
-   Live Tracking
-   Delivery History
-   Meal Plans
-   Menu
-   Weekly Menu
-   Reports
-   Users
-   Settings
-   Audit Logs

## Driver

-   Today
-   Active Delivery
-   Delivery Details
-   Completed Deliveries
-   Profile

------------------------------------------------------------------------

# 56. Important Business Enhancements Added

The following requirements are added because they will prevent
operational problems later:

### A. Enquiry pipeline

Do not directly store only customers. Track the enquiry lifecycle.

### B. Subscription and ad-hoc separation

A monthly subscriber and a one-time caller must not be treated as the
same order type.

### C. Bulk/manpower orders

Support headcount-based commercial orders.

### D. Delivery cutoff

Allow a configurable confirmation cutoff such as 10:00 AM for manpower
lunch orders.

### E. Delivery failure workflow

Drivers must select a failure reason.

### F. Driver assignment

Admin needs to know exactly who is responsible for each order.

### G. Live location only while working

Protect driver privacy and reduce battery/data consumption.

### H. Location staleness

Show "last updated" rather than pretending tracking is live when
GPS/network is unavailable.

### I. Audit logs

Critical operational changes must be traceable.

### J. Historical pricing

Never recalculate old orders using today's prices.

### K. Route-based delivery

Allow future route grouping and optimization.

### L. Delivery pricing configuration

Keep delivery rules configurable rather than hard-coded.

### M. Customer duplicate detection

Phone number should be used to prevent accidental duplicate customers.

### N. Delivery proof

Keep the architecture ready for delivery photo/signature.

### O. Payment tracking

Track paid/pending status even if payment gateway is not integrated
initially.

------------------------------------------------------------------------

# 57. Coding Agent Implementation Rules

The coding agent must:

1.  Build the complete application, not only UI mockups.
2.  Implement working backend APIs.
3.  Implement real MongoDB persistence.
4.  Implement JWT authentication.
5.  Implement RBAC on backend and frontend.
6.  Implement Google Maps location selection.
7.  Implement driver geolocation.
8.  Implement WebSocket live tracking.
9.  Implement real CRUD.
10. Implement real dashboard aggregation.
11. Implement real meal planner persistence.
12. Implement delivery status transitions.
13. Implement responsive UI.
14. Use the supplied Kavi's Kitchen logo.
15. Keep frontend and backend in separate folders.
16. Provide `.env.example` files.
17. Provide seed data.
18. Provide README with exact setup instructions.
19. Do not use fake APIs once backend endpoints are available.
20. Do not hard-code demo data into production screens.
21. Do not break business rules to make UI interactions easier.
22. Keep reusable components modular.
23. Keep API/service logic separate from UI.
24. Use TypeScript types matching backend schemas.
25. Add loading, empty, success and error states.
26. Do not expose secrets.
27. Do not store passwords in plain text.
28. Do not continuously track driver location outside active
    delivery/shift.
29. Do not allow unauthorized users to access another user's/customer's
    data.
30. Keep the code clean enough for another developer to maintain.

------------------------------------------------------------------------

# 58. Definition of Done

The application is considered complete only when the following works
end-to-end:

``` text
LOGIN
  ↓
ROLE DETECTION
  ↓
ADMIN DASHBOARD
  ↓
CREATE CUSTOMER
  ↓
SELECT GOOGLE LOCATION
  ↓
SAVE CUSTOMER
  ↓
CREATE/SELECT MEAL PLAN
  ↓
MEAL PLANNER
  ↓
SELECT BREAKFAST/LUNCH/DINNER
  ↓
SAVE
  ↓
ORDER CREATED
  ↓
ASSIGN DRIVER
  ↓
DRIVER SEES TODAY'S ORDER
  ↓
DRIVER STARTS DELIVERY
  ↓
LOCATION PERMISSION
  ↓
LIVE GPS
  ↓
ADMIN SEES DRIVER ON MAP
  ↓
DRIVER COMPLETES DELIVERY
  ↓
ADMIN SEES DELIVERED
  ↓
DASHBOARD COUNTS UPDATED
```

Also verify:

``` text
AD-HOC ORDER
BULK ORDER
FAILED DELIVERY
DRIVER REASSIGNMENT
CUSTOMER INACTIVE
USER INACTIVE
ORDER CANCELLATION
PAYMENT STATUS
AUDIT LOG
```

------------------------------------------------------------------------

# 59. Final Product Vision

Kavi's Kitchen should feel like a **small professional food-delivery
operations platform**, not a basic CRUD application.

The application should allow the owner/admin to answer immediately:

-   Who are my customers?
-   Who is active?
-   What meals are required today?
-   How many breakfast/lunch/dinner meals are required?
-   Which orders are ready?
-   Which driver has which delivery?
-   Where is my driver right now?
-   Which orders are delivered?
-   Which orders failed?
-   How much revenue did we make?
-   How many subscription customers do we have?
-   How many ad-hoc orders did we receive?
-   Which delivery routes are efficient?
-   Which customers are pending follow-up?

Build V1 with a clean architecture that can later support:

-   Customer self-service portal
-   WhatsApp order integration
-   Online payments
-   Automated SMS/WhatsApp notifications
-   Delivery route optimization
-   Kitchen production dashboard
-   Inventory management
-   Expense tracking
-   Subscription renewal reminders
-   Customer mobile app
-   Driver app/PWA

Do not implement these future features unless needed for V1, but
structure the code so they can be added without rewriting the core
system.
