# Bookkeeper

A project for bookkeeping and financial management.

# Start
```bash
git clone git@github.com:beancount/beangulp.git
cd beangulp/examples
```

Install beangulp and beancount in a `.venv`.

```bash
apt-get install python3-venv # required for virtual env
python3 -m venv .venv # create in subfolder called ".venv"
source ./.venv/bin/activate
pip install beangulp beancount
```

```bash
python import.py extract ./Downloads > tmp.beancount
```

docker run -itd -p 5000:5000 -v ./:/files -e BEANCOUNT_FILE=/files/example.beancount --name fava fava