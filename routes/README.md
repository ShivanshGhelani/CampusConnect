# Route Organization in CampusConnect

## Admin Routes (/routes/admin/)
- admin.py: Main admin panel and event management
- admin_users.py: Admin user management
- auth.py: Authentication and authorization
- dashboard.py: Admin dashboard
- event_form.py: Event form management

## Client Routes (/routes/client/)
- client.py: Public-facing event views and listings
- registration.py: Event registration handling

## Organization Benefits
1. Better separation of concerns between admin and client functionality
2. Improved maintainability and code organization
3. Clearer dependency management
4. Easier to implement role-based access control
5. Better scalability for future features
