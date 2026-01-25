import os
from dotenv import load_dotenv
import json

load_dotenv()

def ai_trading():
	# 1. get upbit chart, 30days
	import pyupbit
	df = pyupbit.get_ohlcv("KRW-ADA", interval="day", count=30)
	# print(df.to_json(orient="records"))
	# print(len(df))

	# 2. give data to ai and get suggestions
	from openai import OpenAI
	client = OpenAI()

	response = client.responses.create(
	model="gpt-4.1",
	input=[
		{
		"role": "system",
		"content": [
			{
			"type": "input_text",
			"text": "You are a ADA coin investing expert.  Tell the user whether to buy, sell or hold at the moment based on the chart data provided. Response in JSON format.\n\nResponse Example:\n{\"reason\": \"some technical reason\", \"decision\": \"buy\"}\n{\"reason\": \"some technical reason\", \"decision\": \"sell\"}\n{\"reason\": \"some technical reason\", \"decision\": \"hold\"}"
			}
		]
		},
		{
		"role": "user",
		"content": [
			{
			"type": "input_text",
			"text": df.to_json(orient="records")
			}
		]
		},
	],
	text={
		"format": {
		"type": "json_object"
		}
	},
	#   reasoning={},
	#   tools=[],
	#   temperature=1,
	#   max_output_tokens=2048,
	#   top_p=1,
	store=True
	)
	result = json.loads(response.output_text)
	print(result)


	# 3. excute the decision

	access = os.getenv("UPBIT_OPEN_API_ACCESS_KEY")
	secret = os.getenv("UPBIT_OPEN_API_SECRET_KEY")
	upbit = pyupbit.Upbit(access, secret)
	# current_cash = upbit.get_balance("KRW")
	tradeing_fee = 0.0005
	current_cash = 10000
	current_ada = upbit.get_balance("ADA")

	print(f'current cash: {upbit.get_balance("KRW")}')
	print(f'current ada: {current_ada}')
	print(f"result: {result}")

	if result["decision"] == "buy":
	    print("buy")
	    my_krw = current_cash
	    if my_krw * (1 - tradeing_fee) > 5000:
	        upbit.buy_market_order("KRW-ADA", my_krw * (1 - tradeing_fee))
	    else:
	        print("not enough krw")
	elif result["decision"] == "sell":
	    print("sell")
	    my_ada = upbit.get_balance("ADA")
	    current_price = pyupbit.get_orderbook(ticker="KRW-ADA")["orderbook_units"][0]["ask_price"]
	    if my_ada * current_price * (1 - tradeing_fee) > 5000:
	        upbit.sell_market_order("KRW-ADA", upbit.get_balance("ADA"))
	    else:
	        print("not enough ada")

	else:
	    print("hold")
	    pass

 if __name__ == "__main__":
    ai_trading()