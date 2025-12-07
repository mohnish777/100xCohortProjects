import gradio as gr
import requests

# You need to get your free API key from https://www.weatherapi.com/
WEATHER_API_KEY = "0b78430ca27c422c90b151536252505"  

def get_temperature(city):
    url = "http://api.weatherapi.com/v1/current.json"
    params = {
        "key": WEATHER_API_KEY,
        "q": city,
        "aqi": "no"
    }
    try:
        resp = requests.get(url, params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            return f"Error: {data['error'].get('message', 'Unknown error')}"
        temp_c = data["current"]["temp_c"]
        location = data["location"]["name"]
        country = data["location"]["country"]
        return f"The current temperature in {location}, {country} is {temp_c}°C."
    except Exception as e:
        return f"Error: {str(e)}"

iface = gr.Interface(
    fn=get_temperature,
    inputs=gr.Textbox(label="Enter city name"),
    outputs=gr.Textbox(label="Temperature"),
    title="City Temperature Checker",
    description="Enter a city name to get the current temperature using WeatherAPI.com."
)

if __name__ == "__main__":
    iface.launch()

