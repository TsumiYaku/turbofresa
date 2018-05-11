# T.U.R.B.O.F.R.E.S.A.  
Turboaggeggio Utile alla Rimorzione di Byte Obrobriosi e di abominevoli  
File da dischi rigidi Riciclati ed altri Elettronici Sistemi di  
Archiviazione di dati.  

## INSTALLAZIONE
Scaricare il file `install.sh` da qualche parte e avviarlo con `sudo`.

## NOTE
Nella `piall@trice`, per evitare di loggarsi come `root` ma avviare lo stesso  
i subprocess che necessitano permessi di root senza dover mettere la password,  
aggiungere le seguenti righe al file `/etc/sudoers`:

`piall ALL=(ALL) NOPASSWD : /sbin/shutdown`  
`piall ALL=(ALL) NOPASSWD : /sbin/badblocks`  

## TODO  
- [X] Chiamare dei subprocess più opportuni (attualmente non lo sono abbastanza).  
- [ ] Implementare un algoritmo di lettura statistica del disco che determini con buona probabilità e rapidità se il disco é piallato o no.  
- [ ] Fare in modo che lo script legga da `lshw -c disk -json` il seriale del disco rigido e che interroghi il db del `tarallo` per ottenere il codice di inventario del disco rigido.  
- [ ] Fare in modo che lo script comunichi con il `tarallo` in modo tale da aggiornare l'inventario automaticamente non appena il disco è piallato.  
