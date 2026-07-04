DATABASES = {
    'default': {
        'ENGINE': 'mssql',
        'NAME': 'Kushki_MERCPD',
        'HOST': '.', # O la instancia de tu SQL Server (ej. localhost\SQLEXPRESS)
        'USER': 'Kushki_Admin', # Si usas autenticaciónt SQL
        'PASSWORD': 'StrongAdminPassword123!',
        'OPTIONS': {
            'driver': 'ODBC Driver 17 for SQL Server',
            'extra_params': 'TrustServerCertificate=yes;',
        },
    }
}
# Nota: Si usas Windows Authentication, omite USER y PASSWORD y añade 'Trusted_Connection': 'yes' en OPTIONS.