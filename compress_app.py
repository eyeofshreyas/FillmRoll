import pickle, numpy as np

similarity = pickle.load(open('similarity.pkl', 'rb'))
print(f"Before: {similarity.shape}, {similarity.dtype}")

similarity = similarity.astype(np.float16)
pickle.dump(similarity, open('similarity.pkl', 'wb'))
print("Done!")
