/* Affiche un plan des sieges colore (comme dans l'app mobile) sur la page
 * d'ajout/modification d'une Reservation dans l'admin Django, pour aider
 * l'agent a voir en un coup d'oeil quels sieges sont deja pris (rouge) ou
 * libres (vert) avant d'en choisir un dans la liste deroulante "Siege". */
(function () {
  "use strict";

  function demarrer() {
    var selectVoyage = document.getElementById("id_voyage");
    var selectSiege = document.getElementById("id_siege");
    if (!selectVoyage || !selectSiege) return;

    var ligneSiege = selectSiege.closest(".form-row") || selectSiege.parentElement;
    var conteneur = document.createElement("div");
    conteneur.id = "plan-sieges-admin";
    conteneur.style.marginTop = "8px";
    ligneSiege.parentElement.insertBefore(conteneur, ligneSiege.nextSibling);

    function rendreMessage(texte) {
      conteneur.innerHTML = '<p style="color:#666;font-style:italic;">' + texte + "</p>";
    }

    function rendreSieges(sieges) {
      if (!sieges || !sieges.length) {
        rendreMessage("Aucun siege trouve pour ce voyage.");
        return;
      }
      var legende =
        '<div style="margin-bottom:6px;font-size:12px;color:#444;">' +
        '<span style="display:inline-block;width:12px;height:12px;background:#3b6d11;border-radius:3px;margin-right:4px;"></span> Libre &nbsp;&nbsp;' +
        '<span style="display:inline-block;width:12px;height:12px;background:#A32D2D;border-radius:3px;margin-right:4px;"></span> Deja reserve' +
        "</div>";
      var grille = document.createElement("div");
      grille.style.cssText =
        "display:flex;flex-wrap:wrap;gap:6px;max-width:420px;";
      sieges.forEach(function (s) {
        var bouton = document.createElement("button");
        bouton.type = "button";
        bouton.textContent = s.numero;
        bouton.disabled = !!s.occupe;
        bouton.title = s.occupe
          ? "Siege " + s.numero + " deja reserve"
          : "Choisir le siege " + s.numero;
        bouton.style.cssText =
          "width:38px;height:38px;border-radius:6px;border:none;color:#fff;font-weight:600;" +
          "cursor:" + (s.occupe ? "not-allowed" : "pointer") + ";" +
          "background:" + (s.occupe ? "#A32D2D" : "#3b6d11") + ";" +
          "opacity:" + (s.occupe ? "0.6" : "1") + ";";
        if (String(selectSiege.value) === String(s.id)) {
          bouton.style.outline = "3px solid #1F3864";
        }
        bouton.addEventListener("click", function () {
          selectSiege.value = s.id;
          selectSiege.dispatchEvent(new Event("change"));
          conteneur.querySelectorAll("button").forEach(function (b) {
            b.style.outline = "none";
          });
          bouton.style.outline = "3px solid #1F3864";
        });
        grille.appendChild(bouton);
      });
      conteneur.innerHTML = legende;
      conteneur.appendChild(grille);
    }

    function chargerSieges() {
      var voyageId = selectVoyage.value;
      if (!voyageId) {
        rendreMessage("Choisissez d'abord un voyage pour voir le plan des sieges.");
        return;
      }
      rendreMessage("Chargement du plan des sieges...");
      fetch("/api/voyage/" + voyageId + "/sieges/")
        .then(function (r) {
          return r.json();
        })
        .then(function (data) {
          if (Array.isArray(data)) {
            rendreSieges(data);
          } else {
            rendreMessage("Impossible de charger le plan des sieges.");
          }
        })
        .catch(function () {
          rendreMessage("Impossible de charger le plan des sieges.");
        });
    }

    selectVoyage.addEventListener("change", chargerSieges);
    chargerSieges();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", demarrer);
  } else {
    demarrer();
  }
})();
