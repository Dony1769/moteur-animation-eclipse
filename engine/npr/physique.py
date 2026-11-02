"""Cheveux et frange : points de contrôle FFD simulés par intégration de Verlet.

Une grille FFD de cheveux est une nappe de points (ny x nx). La rangée du haut est épinglée au
crâne ; les autres points sont libres, reliés à leurs voisins par des contraintes de longueur.

Repère de simulation : celui de la tête, avant skinning. Le FFD agit sur les positions au repos,
puis le squelette tourne l'ensemble. La simulation travaille donc dans ce repère, où la racine
est fixe, et le mouvement de la tête entre comme forces d'inertie :
  - accélération d'entraînement : -(R^T) a_pivot (le pivot de la tête peut être porté par un parent) ;
  - Euler : -α ẑ×r ; centrifuge : +ω² r ; Coriolis : -2 ω ẑ×v  (r = position relative au pivot).
Gravité : R^T g, avec g = (0, +GRAVITE) (y vers le bas dans l'image).

Intégration de Verlet à pas fixe (dt = 1/240 s par défaut) :
    x_{n+1} = x_n + d · (x_n - x_{n-1}) + a · dt²,   d = amortissement^(dt · 60)
Les contraintes de distance se corrigent en proportion des masses inverses : un point épinglé
(masse inverse 0) ne bouge pas, et le point libre absorbe la correction entière.

Les décalages (x - repos) vont dans GrilleFFD.decalages, puis le FFD déforme les calques de cheveux.
"""
import numpy as np

from .rig import _rotation

GRAVITE = 540.0          # px/s² : équivalent à 0,15 px/image² à 60 images/s (valeur du document de conception)
DT = 1.0 / 240.0


def forces_fictives(r, v, omega, alpha):
    """Accélérations apparentes dans le repère de la tête (N, 2) pour positions r et vitesses v.

    r : positions relatives au pivot ; v : vitesses dans le repère de la tête.
    ẑ×(x, y) = (-y, x). Euler : -α ẑ×r ; centrifuge : -ω×(ω×r) = ω² r ; Coriolis : -2ω ẑ×v.
    """
    r = np.asarray(r, np.float64)
    v = np.asarray(v, np.float64)
    euler = -alpha * np.stack([-r[:, 1], r[:, 0]], axis=1)
    centrifuge = omega * omega * r
    coriolis = -2.0 * omega * np.stack([-v[:, 1], v[:, 0]], axis=1)
    return euler + centrifuge + coriolis


class ChevelureSimulee:
    """Nappe de cheveux (grille FFD) simulée par Verlet, attachée à un os du squelette.

    grille : GrilleFFD dont les points au repos servent de positions initiales ;
    squelette : rig.Squelette ; os_nom : os auquel la chevelure est attachée ;
    mouvement : objet avec .pose(t) -> {nom: angle} (ex. rig.Timeline).
    epingle_ligne : indice de la rangée épinglée (0 = haut de la grille).
    """

    def __init__(self, grille, squelette, os_nom, mouvement, *, epingle_ligne=0,
                 amortissement=0.98, iterations=8, gravite=GRAVITE, dt=DT):
        if os_nom not in squelette.index:
            raise ValueError(f"os inconnu : {os_nom}")
        if not 0 <= epingle_ligne < grille.ny:
            raise ValueError("rangée épinglée hors de la grille")
        if not 0.0 < amortissement <= 1.0:
            raise ValueError("amortissement hors de ]0, 1]")
        if dt <= 0 or iterations < 1:
            raise ValueError("pas de temps ou itérations non positifs")
        self.grille = grille
        self.squelette = squelette
        self.k = squelette.index[os_nom]
        self.mouvement = mouvement
        self.amortissement = float(amortissement)
        self.iterations = int(iterations)
        self.gravite = float(gravite)
        self.dt = float(dt)
        self.t = 0.0

        ny, nx = grille.ny, grille.nx
        self.repos = grille.repos.reshape(-1, 2).astype(np.float64)
        self.P = self.repos.copy()
        self.Q = self.repos.copy()
        self.v = np.zeros_like(self.repos)
        epingle = np.zeros((ny, nx), bool)
        epingle[epingle_ligne, :] = True
        self.epingle = epingle.ravel()
        self.inv_masse = np.where(self.epingle, 0.0, 1.0)
        self.contraintes = self._contraintes(ny, nx)

    def _contraintes(self, ny, nx):
        """Liens structurels horizontaux et verticaux : (i, j, longueur au repos)."""
        idx = np.arange(ny * nx).reshape(ny, nx)
        liens = []
        for i, j in [(idx[:, :-1], idx[:, 1:]), (idx[:-1, :], idx[1:, :])]:
            for a, b in zip(i.ravel(), j.ravel()):
                liens.append((int(a), int(b), float(np.linalg.norm(self.repos[a] - self.repos[b]))))
        return liens

    # ---- mouvement de la tête --------------------------------------------------------

    def _angle_chaine(self, pose, k):
        """Angle total du repère de l'os k : somme des rotations de k et de ses ancêtres (rotations 2D)."""
        total = 0.0
        while k is not None:
            o = self.squelette.os[k]
            total += float(pose.get(o.nom, 0.0))
            k = o.parent
        return total

    def _pivot_monde(self, pose):
        """Position du pivot de l'os dans le repère image, après les rotations des parents."""
        o = self.squelette.os[self.k]
        p = np.array([o.pivot[0], o.pivot[1], 1.0])
        if o.parent is None:
            return p[:2]
        G = self.squelette.matrices(pose)[o.parent]
        return (G @ p)[:2]

    def mouvement_au(self, t, h=1e-3):
        """(θ, ω, α, a_pivot) à l'instant t, par différences finies centrées sur le mouvement."""
        def angle(s):
            return self._angle_chaine(self.mouvement.pose(s), self.k)

        th = angle(t)
        om = (angle(t + h) - angle(t - h)) / (2 * h)
        al = (angle(t + h) - 2 * th + angle(t - h)) / (h * h)

        def pivot(s):
            return self._pivot_monde(self.mouvement.pose(s))
        a_piv = (pivot(t + h) - 2 * pivot(t) + pivot(t - h)) / (h * h)
        return th, om, al, a_piv

    # ---- intégration -----------------------------------------------------------------

    def pas(self, dt=None):
        """Un pas de Verlet à l'instant courant. Met à jour la grille (décalages) et le temps."""
        dt = self.dt if dt is None else float(dt)
        th, om, al, a_piv = self.mouvement_au(self.t)
        R_inv = _rotation(th)[:2, :2].T
        g_monde = np.array([0.0, self.gravite])
        a_ext = R_inv @ (g_monde - a_piv)
        r = self.P - self._centre_pivot()
        fict = forces_fictives(r, self.v, om, al)
        a = a_ext[None, :] + fict

        amort = self.amortissement ** (dt * 60.0)
        libre = ~self.epingle
        nouveau = self.P + amort * (self.P - self.Q) + a * dt * dt
        nouveau[self.epingle] = self.repos[self.epingle]
        self.Q = self.P
        self.P = nouveau
        self.P[self.epingle] = self.repos[self.epingle]
        self.Q[self.epingle] = self.repos[self.epingle]
        self._contraindre()
        self.v = np.where(libre[:, None], (self.P - self.Q) / dt, 0.0)
        self.t += dt
        self.pousser_vers_grille()

    def _centre_pivot(self):
        """Pivot de l'os exprimé dans le repère des points de la grille (repos, avant skinning)."""
        o = self.squelette.os[self.k]
        return np.asarray(o.pivot, np.float64)

    def _contraindre(self):
        P, w = self.P, self.inv_masse
        for _ in range(self.iterations):
            for i, j, L in self.contraintes:
                delta = P[j] - P[i]
                d = np.linalg.norm(delta)
                somme = w[i] + w[j]
                if d < 1e-12 or somme == 0.0:
                    continue
                corr = delta * ((d - L) / d)
                P[i] += corr * (w[i] / somme)
                P[j] -= corr * (w[j] / somme)

    def avancer(self, t_cible):
        """Intègre jusqu'à t_cible (pas fixe, dernier pas partiel). Ne recule jamais."""
        if t_cible < self.t - 1e-12:
            raise ValueError("la simulation ne revient pas en arrière")
        while self.t < t_cible - 1e-12:
            self.pas(min(self.dt, t_cible - self.t))

    def pousser_vers_grille(self):
        """Écrit les décalages courants dans GrilleFFD.decalages (ny, nx, 2)."""
        self.grille.decalages = (self.P - self.repos).reshape(self.grille.ny, self.grille.nx, 2)

    def longueurs_relatives(self):
        """Écart relatif maximal des longueurs de liens à leur valeur au repos (diagnostic)."""
        ecarts = [abs(np.linalg.norm(self.P[j] - self.P[i]) - L) / L for i, j, L in self.contraintes if L > 0]
        return max(ecarts, default=0.0)
