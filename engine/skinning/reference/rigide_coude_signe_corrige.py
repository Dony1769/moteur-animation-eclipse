exec(open('volume_interpenetration.py').read().split('for Rs in (0.07,):')[0])
ax = -ax   # erreur 110 : le signe était inversé (hyperextension)
for th in (0, 30, 60, 90, 120, 145):
    v, fu, ff = mesure(th, 0.07)
    print(f"RIGIDE_SIGNE_CORRIGE θ={th}: interpénétration hors sphère {None if v is None else round(float(v),3)} cm3", flush=True)
