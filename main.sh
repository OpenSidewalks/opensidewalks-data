# docker build --tag dm . && docker run -v $(pwd):/sourcedata dm all cities/seattle
docker build --tag dm . && docker run -v $(pwd):/sourcedata dm finalize cities/seattle
