<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Centered Search Bar</title>
    <style>
        /* Basic CSS to center the search bar */
        body {
            margin: 0;
            padding: 0;
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            font-family: Arial, sans-serif;
            background-color: #f0f0f0;
        }

        /* Style for the input */
        input {
            width: 400px;
            padding: 15px;
            border-radius: 25px;
            border: 2px solid #ccc;
            outline: none;
            font-size: 16px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            transition: border 0.3s ease;
        }

        /* Style for the input on focus */
        input:focus {
            border-color: #4285f4;
        }
    </style>
</head>

<body>

    <!-- Widget JavaScript bundle -->
    <script src="https://cloud.google.com/ai/gen-app-builder/client?hl=en_GB"></script>

    <!-- Search widget element -->
    <gen-search-widget
      configId="42d7a6f0-38be-4aba-bf7e-cdb63596f581"
      triggerId="searchWidgetTrigger">
    </gen-search-widget>

    <!-- Centered search input -->
    <input placeholder="Search here" id="searchWidgetTrigger" />

    <script>
        // Initialize the widget and ensure it's connected to the input field
        document.getElementById('searchWidgetTrigger').addEventListener('click', function () {
            // Simulate opening the search widget when the input is clicked
            const searchWidget = document.querySelector('gen-search-widget');
            searchWidget.open();
        });
    </script>

</body>

</html>
