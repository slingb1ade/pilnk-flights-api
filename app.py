from flask import Flask, request, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'PiLNK Flight Search'})

@app.route('/search', methods=['POST'])
def search():
    try:
        from fli.search import SearchFlights
        from fli.models import (FlightSearchFilters, FlightSegment, Airport,
                                PassengerInfo, SeatType, MaxStops, TripType)

        data = request.get_json()
        origin      = data.get('origin', 'AKL').upper()
        destination = data.get('destination', 'SYD').upper()
        date        = data.get('date', '')
        adults      = int(data.get('adults', 1))
        seat        = data.get('seat', 'ECONOMY').upper()
        stops       = data.get('stops', 'ANY').upper()

        try:
            dep = getattr(Airport, origin)
            arr = getattr(Airport, destination)
        except AttributeError as e:
            return jsonify({'error': f'Unknown airport code: {str(e)}'}), 400

        seat_map = {
            'ECONOMY': SeatType.ECONOMY,
            'BUSINESS': SeatType.BUSINESS,
            'FIRST': SeatType.FIRST,
            'PREMIUM_ECONOMY': SeatType.PREMIUM_ECONOMY
        }
        stops_map = {
            'ANY': MaxStops.ANY,
            'NON_STOP': MaxStops.NON_STOP,
            'ONE_STOP': MaxStops.ONE_STOP_OR_FEWER
        }

        filters = FlightSearchFilters(
            trip_type=TripType.ONE_WAY,
            passenger_info=PassengerInfo(adults=adults),
            flight_segments=[FlightSegment(
                departure_airport=[[dep, 0]],
                arrival_airport=[[arr, 0]],
                travel_date=date
            )],
            seat_type=seat_map.get(seat, SeatType.ECONOMY),
            stops=stops_map.get(stops, MaxStops.ANY)
        )

        results = SearchFlights().search(filters)

        flights = []
        for r in results[:20]:
            legs = []
            for leg in r.legs:
                legs.append({
                    'airline': leg.airline.value if leg.airline else '',
                    'flight_number': leg.flight_number or '',
                    'departure_airport': leg.departure_airport.name if leg.departure_airport else '',
                    'arrival_airport': leg.arrival_airport.name if leg.arrival_airport else '',
                    'departure_time': leg.departure_datetime.strftime('%H:%M') if leg.departure_datetime else '',
                    'arrival_time': leg.arrival_datetime.strftime('%H:%M') if leg.arrival_datetime else '',
                    'duration': leg.duration or 0,
                })
            flights.append({
                'price': r.price,
                'duration': r.duration,
                'stops': r.stops,
                'legs': legs
            })

        return jsonify({'flights': flights, 'count': len(results)})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
