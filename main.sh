# docker build --tag dm . && docker run -v $(pwd):/sourcedata dm fetch cities/seattle
# docker build --tag dm . && docker run -v $(pwd):/sourcedata dm standardize cities/seattle
# docker build --tag dm . && docker run -v $(pwd):/sourcedata dm redraw cities/seattle
# docker build --tag dm . && docker run -v $(pwd):/sourcedata dm annotate cities/seattle
# docker build --tag dm . && docker run -v $(pwd):/sourcedata dm network cities/seattle
# docker build --tag dm . && docker run -v $(pwd):/sourcedata dm incline cities/seattle
# docker build --tag dm . && docker run -v $(pwd):/sourcedata dm finalize cities/seattle
docker build --tag dm . && docker run -v $(pwd):/sourcedata dm all cities/seattle
