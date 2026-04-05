# import os
# import pandas as pd 
# from sklearn.metrics.pairwise import cosine_similarity
# import numpy as np 
# import joblib 
# import requests
# from google import genai
# # from config import api_key

# client = genai.Client(api_key="AIzaSyC6w7DWlH8P8m-CDEZNS3v_TIjHxPuRHIY")


# def create_embedding(text_list):
#     # https://github.com/ollama/ollama/blob/main/docs/api.md#generate-embeddings
#     r = requests.post("http://localhost:11434/api/embed", json={
#         "model": "bge-m3",
#         "input": text_list
#     })

#     embedding = r.json()["embeddings"] 
#     return embedding

# def inference(prompt):
#     r = requests.post("http://localhost:11434/api/generate", json={
#         # "model": "deepseek-r1",
#         "model": "llama3.2",
#         "prompt": prompt,
#         "stream": False
#     })

#     response = r.json()
#     print(response)
#     return response

# def inference_openai(prompt):
#     print("THinking")
#     """
#     Call Gemini via google.genai. Return a plain string containing the model output.
#     Uses response.text if present, otherwise falls back to str(response).
#     """
#     try:
#         response = client.models.generate_content(
#             model="gemini-2.5-flash",
#             contents=prompt
#         )
#         # Preferred attribute for generated text
#         if getattr(response, "text", None) is not None:
#             return response.text
#         # Some SDK versions might expose different attrs; fall back to parsed or str()
#         if getattr(response, "parsed", None) is not None:
#             # parsed might be structured — convert to string
#             return str(response.parsed)
#         return str(response)
#     except Exception as e:
#         # raise a clearer error for debugging
#         raise RuntimeError(f"GenAI generate_content failed: {e}") from e


# # --- Later in your script, replace the use of inference_openai and file write as below ---

# #response_text = inference_openai(prompt)



# df = joblib.load('embeddings.joblib')


# incoming_query = input("Ask a Question: ")
# question_embedding = create_embedding([incoming_query])[0] 

# # Find similarities of question_embedding with other embeddings
# # print(np.vstack(df['embedding'].values))
# # print(np.vstack(df['embedding']).shape)
# similarities = cosine_similarity(np.vstack(df['embedding']), [question_embedding]).flatten()
# # print(similarities)
# top_results = 5
# max_indx = similarities.argsort()[::-1][0:top_results]
# # print(max_indx)
# new_df = df.loc[max_indx] 
# # print(new_df[["title", "number", "text"]])

# prompt = f'''I am teaching web development in my Sigma web development course. Here are video subtitle chunks containing video title, video number, start time in seconds, end time in seconds, the text at that time:

# {new_df[["title", "number", "start", "end", "text"]].to_json(orient="records")}
# ---------------------------------
# "{incoming_query}"
# User asked this question related to the video chunks, you have to answer in a human way (dont mention the above format, its just for you) where and how much content is taught in which video (in which video and at what timestamp) and guide the user to go to that particular video. If user asks unrelated question, tell him that you can only answer questions related to the course
# '''
# with open("prompt.txt", "w") as f:
#     f.write(prompt)

# # response = inference(prompt)["response"]
# # print(response)

# response = inference_openai(prompt)
# print(response)

# with open("response.txt", "w") as f:
#     f.write(response)
# # for index, item in new_df.iterrows():
# #     print(index, item["title"], item["number"], item["text"], item["start"], item["end"])




