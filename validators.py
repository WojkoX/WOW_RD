def waliduj_protokol(protokol, suma_kandydatow):
    bledy = []
    p = protokol
    s = suma_kandydatow or 0
    
    if (p.l_kart_wydan or 0) > (p.l_uprawn or 0):
        bledy.append("R1: Karty wydane > Uprawnieni")
    if (p.l_kart_otrzym or 0) != ((p.l_kart_niewyk or 0) + (p.l_kart_wydan or 0)):
        bledy.append("R2: BĹ‚Ä…d bilansu kart otrzymanych")
    if (p.l_kart_wyjet or 0) != ((p.l_kart_wyjet_waz or 0) + (p.l_kart_wyjet_niewaz or 0)):
        bledy.append("R3: BĹ‚Ä…d sumy kart wyjÄ™tych (WaĹĽne+NiewaĹĽne)")
    if (p.l_kart_wyjet_waz or 0) != ((p.l_glos_waz or 0) + (p.l_glos_niewaz or 0)):
        bledy.append("R4: BĹ‚Ä…d sumy gĹ‚osĂłw w kartach waĹĽnych")
    if (p.l_glos_niewaz or 0) != ((p.l_glos_niewaz_zlyx or 0) + (p.l_glos_niewaz_inne or 0)):
        bledy.append("R5: BĹ‚Ä…d przyczyn niewaĹĽnoĹ›ci")
    if (p.l_glos_waz or 0) != s:
        bledy.append(f"R6: Suma gĹ‚osĂłw na kandydatĂłw ({s}) != GĹ‚osy waĹĽne ({p.l_glos_waz})")
    
    return bledy
