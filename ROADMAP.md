# OWNd — Roadmap

Stato al 2026-08-07 · stabile **v1.0.11** · prossimo ciclo **v1.0.12-beta**

## Fatto in 1.0.11

La versione estende il parsing della termoregolazione emerso da un impianto BTicino 3550 / MyHomeServer1:

- separa correttamente le dimensioni 12 e 14, evitando che lo stato locale/effective e lo stato centrale si sovrascrivano;
- espone i valori grezzi della dimensione 13 e riconosce lo stato `local_override`;
- interroga esplicitamente la dimensione 19 durante l'aggiornamento completo;
- allinea la versione esposta a runtime con i metadata del pacchetto.

La regressione automatica comprende sei test dedicati alla termoregolazione. Ruff, mypy e i test unitari vengono eseguiti dalla CI a ogni push e pull request.

La versione è stata validata su hardware reale con MyHomeServer1 (12 zone di
termoregolazione, 49 luci e 3 misuratori F520) e con un soak test sull'impianto
MH201 di riferimento. La promozione stabile è coordinata con MyHOME 0.9.87.

## In beta 1.0.12

La prima beta è una baseline versionata, operativamente identica alla stabile 1.0.11. I
interventi sono stati introdotti in iterazioni separate e coperti da test:

- rendere strettamente *fail-closed* la negoziazione legacy e HMAC: una risposta inattesa
  dopo l'invio della password deve chiudere la sessione, mai essere interpretata come
  successo;
- aggiungere un limite complessivo di tempo e frame alla lettura delle risposte di
  segnalazione, oltre al timeout applicato oggi al singolo frame;
- garantire il `close()` delle sessioni temporanee anche nei percorsi eccezionali dei
  metodi helper e di `test_connection()`;
- validare la password numerica con un errore controllato, evitando un `ValueError` grezzo;
- completare l'inizializzazione difensiva degli eventi energia con WHERE non supportato e
  gestire correttamente il calcolo annuale quando la data corrente è il 29 febbraio;
- ampliare la copertura dei parser solo quando sono disponibili frame reali e hardware su
  cui verificare il comportamento.
